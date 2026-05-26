"""Детерминированный анализатор рынка коммерческой недвижимости.

Работает на основе 4 CSV-файлов из CRM:
- active_rent.csv / active_sale.csv — активные объекты
- closed_rent.csv / closed_sale.csv — закрытые сделки

Плюс сводные таблицы грейдов:
- RBN_DEMAND_MATRIX.csv — матрица район×площадь×цена
- RBN_DEMAND_DISTRICTS_V2.csv — грейды районов
- RBN_DEMAND_AREAS_V2.csv — грейды площадей
- RBN_MAX_SEGMENT_BENCHMARKS_2026.csv — бенчмарки сегментов
"""
from __future__ import annotations

import csv
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from statistics import median

logger = logging.getLogger(__name__)


@dataclass
class ObjectRecord:
    obj_type: str
    deal_type: str
    district: str
    area: float
    price: float
    price_sqm: float


@dataclass
class DistrictGrade:
    deal_type: str
    obj_type: str
    district: str
    count: int
    share: float
    grade: str
    rank: int


@dataclass
class AreaGrade:
    deal_type: str
    obj_type: str
    area_range: str
    count: int
    share: float
    grade: str
    avg_price: float
    median_price: float


@dataclass
class SegmentBenchmark:
    segment: str
    area_core: str
    price_benchmark: str
    cap_rate_target: str
    liquidity_index: float
    exposure_days: str


class MarketAnalyzer:
    """Анализатор рынка на реальных данных CRM."""

    TYPE_ALIASES = {
        "Офис": "Офисное помещение",
        "Офисное помещение": "Офисное помещение",
        "Торговое помещение": "Торговое помещение",
        "Склад/База": "База/склад/производство",
        "Склад": "База/склад/производство",
        "База/склад/производство": "База/склад/производство",
        "Стрит-ритейл / ПСН": "Свободного назначения",
        "ПСН": "Свободного назначения",
        "Свободного назначения": "Свободного назначения",
    }

    BENCHMARK_PRIORITY = {
        "Офисное помещение": ["Офисы малые", "Офисы средние", "Офисы большие"],
        "Торговое помещение": ["Стрит-ритейл (трафиковый)", "ТЦ (малые площади)"],
        "База/склад/производство": ["Склады малые", "Склады средние", "Склады большие"],
        "Свободного назначения": ["Стрит-ритейл (у дома)", "Коммерция в новых ЖК"],
    }

    # Маппинг: ключевое слово из CRM → район в базе грейдов
    # Восточный АО (ВАО)
    # Калининский АО (КАО)
    # Ленинский АО (ЛАО)
    # Центральный АО (ЦАО)
    DISTRICT_ALIASES: dict[str, list[str]] = {
        "Восточный р-н": [
            "восточный", "широтная", "мжк",
            "малахово", "ново-патрушево", "войновка",
            "1 мкр", "2 мкр", "3 мкр", "4 мкр", "5 мкр", "6 мкр",
            "один микрорайон", "первый мкр",
        ],
        "Калининский округ": [
            "калининский", "док", "плеханово", "южный", "комарово",
            "метелева", "воронина", "княжево", "рощино", "маяк",
            "московский тракт", "червишевский", "тюменская слобода",
            "дударев", "европейский", "ольховка",
            "перевалово", "утёшево", "утешево",
            "тюменский р-н", "тюменский район",
        ],
        "Ленинский округ": [
            "ленинский", "антипино", "гилёво", "гилево", "лесобаза",
            "тарманы", "мыс", "казачьи луга", "копытово", "энтузиастов",
            "букино", "рабочий посёлок", "матмасы", "быкова", "зайкова",
        ],
        "Центр": [
            "центр", "центральный", "заречный", "заречье",
            "студгородок", "историч", "драмтеатр", "кпд",
            "дом печати", "тычковка",
            "50 лет влксм", "50 лет", "дом обороны",
        ],
    }

    def __init__(self) -> None:
        self.docs_dir = self._resolve_docs_dir()

    def _resolve_docs_dir(self) -> Path:
        env_docs = os.getenv("RBN_DOCS_DIR")
        if env_docs:
            return Path(env_docs).resolve()
        return (Path(__file__).resolve().parents[1] / "docs").resolve()

    # ─── Загрузка данных ───

    @staticmethod
    def _to_float(value: object) -> float:
        if value is None:
            return 0.0
        text = str(value).strip().replace(" ", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _load_objects_csv(self, filename: str) -> list[ObjectRecord]:
        path = self.docs_dir / filename
        if not path.exists():
            logger.warning("CSV не найден: %s", path)
            return []
        rows: list[ObjectRecord] = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                area = self._to_float(row.get("Площадь"))
                price = self._to_float(row.get("Цена"))
                if area < 5 or price <= 0:
                    continue
                rows.append(ObjectRecord(
                    obj_type=row.get("Тип объекта", ""),
                    deal_type=row.get("Тип заявки", ""),
                    district=row.get("Район", ""),
                    area=area,
                    price=price,
                    price_sqm=round(price / area, 0),
                ))
        return rows

    @lru_cache(maxsize=1)
    def _active_rent(self) -> list[ObjectRecord]:
        return self._load_objects_csv("active_rent.csv")

    @lru_cache(maxsize=1)
    def _active_sale(self) -> list[ObjectRecord]:
        return self._load_objects_csv("active_sale.csv")

    @lru_cache(maxsize=1)
    def _closed_rent(self) -> list[ObjectRecord]:
        return self._load_objects_csv("closed_rent.csv")

    @lru_cache(maxsize=1)
    def _closed_sale(self) -> list[ObjectRecord]:
        return self._load_objects_csv("closed_sale.csv")

    def _all_rent(self) -> list[ObjectRecord]:
        return self._active_rent() + self._closed_rent()

    def _all_sale(self) -> list[ObjectRecord]:
        return self._active_sale() + self._closed_sale()

    @lru_cache(maxsize=1)
    def _district_grades(self) -> list[DistrictGrade]:
        path = self.docs_dir / "RBN_DEMAND_DISTRICTS_V2.csv"
        if not path.exists():
            return []
        rows: list[DistrictGrade] = []
        with path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(DistrictGrade(
                    deal_type=row.get("deal_type", ""),
                    obj_type=row.get("obj_type", ""),
                    district=row.get("district", ""),
                    count=int(row.get("count", 0)),
                    share=self._to_float(row.get("share_pct")),
                    grade=row.get("grade", "C"),
                    rank=int(row.get("rank", 99)),
                ))
        return rows

    @lru_cache(maxsize=1)
    def _area_grades(self) -> list[AreaGrade]:
        path = self.docs_dir / "RBN_DEMAND_AREAS_V2.csv"
        if not path.exists():
            return []
        rows: list[AreaGrade] = []
        with path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(AreaGrade(
                    deal_type=row.get("deal_type", ""),
                    obj_type=row.get("obj_type", ""),
                    area_range=row.get("area_range", ""),
                    count=int(row.get("count", 0)),
                    share=self._to_float(row.get("share_pct")),
                    grade=row.get("grade", "C"),
                    avg_price=self._to_float(row.get("avg_price")),
                    median_price=self._to_float(row.get("median_price")),
                ))
        return rows

    @lru_cache(maxsize=1)
    def _segment_benchmarks(self) -> list[SegmentBenchmark]:
        path = self.docs_dir / "RBN_MAX_SEGMENT_BENCHMARKS_2026.csv"
        if not path.exists():
            return []
        rows: list[SegmentBenchmark] = []
        with path.open("r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(SegmentBenchmark(
                    segment=row.get("segment", ""),
                    area_core=row.get("area_core", ""),
                    price_benchmark=row.get("price_benchmark", ""),
                    cap_rate_target=row.get("cap_rate_target", ""),
                    liquidity_index=self._to_float(row.get("liquidity_index")),
                    exposure_days=row.get("exposure_days", ""),
                ))
        return rows

    # ─── Поиск грейдов ───

    def _area_bucket(self, area: float) -> str:
        lo = int((area - 1) // 10) * 10 + 1
        return f"{lo}-{lo + 9}"

    def _find_area_grade(self, obj_type: str, area: float, deal_key: str) -> AreaGrade | None:
        bucket = self._area_bucket(area)
        for g in self._area_grades():
            if g.deal_type == deal_key and g.obj_type == obj_type and g.area_range == bucket:
                return g
        return None

    def _find_district_grade(self, obj_type: str, district: str, deal_key: str) -> DistrictGrade | None:
        if not district:
            return None
        candidates = [d for d in self._district_grades()
                       if d.deal_type == deal_key and d.obj_type == obj_type]
        # 1. Точное совпадение
        for d in candidates:
            if d.district == district:
                return d
        # 2. Район содержится в запросе или наоборот
        dist_lower = district.lower()
        for d in candidates:
            if d.district.lower() in dist_lower or dist_lower in d.district.lower():
                return d
        # 3. Совпадение по первому слову (Восточный / Широтная → Восточный р-н)
        first_word = re.split(r"[\s/,·]+", district.strip())[0].lower()
        if len(first_word) >= 3:
            matches = [d for d in candidates if d.district.lower().startswith(first_word)]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                rn = [d for d in matches if "р-н" in d.district]
                if rn:
                    return rn[0]
                return min(matches, key=lambda d: d.rank)
        # 4. Поиск через DISTRICT_ALIASES (Широтная → Восточный р-н)
        for canonical, aliases in self.DISTRICT_ALIASES.items():
            if any(alias in dist_lower for alias in aliases):
                for d in candidates:
                    if d.district == canonical:
                        return d
        return None

    def _find_benchmark(self, obj_type: str, area: float) -> SegmentBenchmark | None:
        segments = self.BENCHMARK_PRIORITY.get(obj_type, [])
        for s in self._segment_benchmarks():
            if s.segment in segments:
                return s
        return None

    # ─── Расчёты ───

    def _filter_objects(
        self, objects: list[ObjectRecord], obj_type: str,
        district: str | None = None, area: float | None = None, area_tolerance: float = 0.3,
    ) -> list[ObjectRecord]:
        result = [o for o in objects if o.obj_type == obj_type]
        if district:
            # Точное совпадение
            district_filtered = [o for o in result if o.district == district]
            if len(district_filtered) < 3:
                # Нечёткое: первое слово
                first_word = re.split(r"[\s/,·]+", district.strip())[0].lower()
                if len(first_word) >= 3:
                    district_filtered = [o for o in result if o.district.lower().startswith(first_word)]
            if len(district_filtered) >= 3:
                result = district_filtered
        if area:
            lo, hi = area * (1 - area_tolerance), area * (1 + area_tolerance)
            area_filtered = [o for o in result if lo <= o.area <= hi]
            if len(area_filtered) >= 3:
                result = area_filtered
        return result

    def _median_price_sqm(self, objects: list[ObjectRecord]) -> float | None:
        if not objects:
            return None
        prices = [o.price_sqm for o in objects if o.price_sqm > 0]
        return round(median(prices)) if prices else None

    def _compute_mos(self, obj_type: str, is_rent: bool) -> float | None:
        """Months of Supply."""
        active = self._active_rent() if is_rent else self._active_sale()
        closed = self._closed_rent() if is_rent else self._closed_sale()
        active_n = sum(1 for o in active if o.obj_type == obj_type)
        closed_n = sum(1 for o in closed if o.obj_type == obj_type)
        if closed_n == 0:
            return None
        months = max(1, (date.today().year - 2025) * 12 + date.today().month)
        return round(active_n / (closed_n / months), 1)

    @staticmethod
    def _parse_range(text: str) -> tuple[float | None, float | None]:
        text = (text or "").replace(" ", "").replace("%", "")
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)", text)
        if m:
            return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
        return None, None

    # ─── Главный метод ───

    def analyze(
        self,
        deal_type: str,
        obj_type: str,
        area: str,
        price: str,
        district: str,
        is_gab: bool = False,
        monthly_rent: float = 0,
        indexation_pct: float = 5.0,
    ) -> str:
        area_val = self._to_float(re.sub(r"[^\d,.]", "", str(area)))
        price_val = self._to_float(re.sub(r"[^\d,.]", "", str(price)))
        if area_val <= 0:
            return ""

        canon = self.TYPE_ALIASES.get(obj_type, obj_type)
        price_sqm = round(price_val / area_val) if price_val > 0 else 0
        is_rent = "аренд" in deal_type.lower() or "сдать" in deal_type.lower()
        deal_key = "аренда" if is_rent else "продажа"

        # Собираем данные
        active = self._active_rent() if is_rent else self._active_sale()
        closed = self._closed_rent() if is_rent else self._closed_sale()

        # Медианы по району
        closed_district = self._filter_objects(closed, canon, district, area_val)
        med_closed_d = self._median_price_sqm(closed_district)

        # Медианы по городу
        closed_city = self._filter_objects(closed, canon, area=area_val)
        med_closed_c = self._median_price_sqm(closed_city)

        # Грейды
        area_grade = self._find_area_grade(canon, area_val, deal_key)
        dist_grade = self._find_district_grade(canon, district, deal_key)
        benchmark = self._find_benchmark(canon, area_val)

        # Ликвидность
        liq = self._calc_liquidity(area_grade, dist_grade, price_sqm, med_closed_d or med_closed_c, benchmark)

        # ═══ ФОРМИРУЕМ ОТЧЁТ ═══
        deal_label = "Аренда" if is_rent else ("Продажа · ГАБ" if is_gab else "Продажа")
        price_label = "ставка" if is_rent else "цена"

        lines: list[str] = []
        lines.append("<b>📊 Аналитика объекта</b>")
        lines.append(f"{canon} · {area_val:.0f} м² · {deal_label}")
        # Район + грейд
        dist_info = district or "район не указан"
        if dist_grade:
            gl_d = {"A+": "🟢", "A": "🟢", "B": "🟡", "C": "🔴"}
            dist_info += f" · {gl_d.get(dist_grade.grade, '')} район грейд {dist_grade.grade}"
        lines.append(f"📍 {dist_info}")
        lines.append("")

        # ▎1. Спрос
        lines.append("<b>▎Спрос на объект</b>")
        user_bucket = self._area_bucket(area_val)
        user_in_core = area_grade and area_grade.grade in ("A+", "A")
        if user_in_core:
            lines.append(f"    🟢 Ваш диапазон {user_bucket} м² — в ядре спроса (грейд {area_grade.grade})")
        elif area_grade:
            gl = {"B": "средний спрос", "C": "низкий спрос"}
            emoji = "🟡" if area_grade.grade == "B" else "🔴"
            lines.append(f"    {emoji} Ваш диапазон {user_bucket} м² — вне ядра (грейд {area_grade.grade}, {gl.get(area_grade.grade, '')})")
        else:
            lines.append(f"    ⚠️ Нет данных для диапазона {user_bucket} м²")
        if area_grade:
            lines.append(f"    Конкурентов в диапазоне: {area_grade.count} объектов")
        lines.append("")

        # ▎2. Цена и аналоги
        active_comps = self._filter_objects(active, canon, district, area_val, 0.3)
        closed_comps = self._filter_objects(closed, canon, district, area_val, 0.3)
        in_district = bool(district)
        if len(active_comps) < 3 and district:
            active_comps = self._filter_objects(active, canon, None, area_val, 0.3)
            in_district = False
        if len(closed_comps) < 3 and district:
            closed_comps = self._filter_objects(closed, canon, None, area_val, 0.3)

        ref_price = None
        delta_pct = 0.0

        if price_sqm > 0:
            lines.append("<b>▎Цена и аналоги</b>")
            p_fmt = f"{price_val:,.0f}".replace(",", " ")
            sq_fmt = f"{price_sqm:,}".replace(",", " ")
            lines.append(f"    Ваша {price_label}: {p_fmt} {'₽/мес' if is_rent else '₽'} ({sq_fmt} ₽/м²)")

            scope = district if in_district else "весь город"
            med_sold = self._median_price_sqm(closed_comps)
            med_active = self._median_price_sqm(active_comps)

            if active_comps and med_active:
                ma_fmt = f"{med_active:,}".replace(",", " ")
                lines.append(f"    Активные ({scope}): {len(active_comps)} шт., медиана {ma_fmt} ₽/м²")
            if closed_comps and med_sold:
                mc_fmt = f"{med_sold:,}".replace(",", " ")
                lines.append(f"    Сделки ({scope}): {len(closed_comps)} шт., медиана {mc_fmt} ₽/м²")
                delta_vs_sold = ((price_sqm - med_sold) / med_sold) * 100
                if delta_vs_sold > 5:
                    verb = "сданных" if is_rent else "проданных"
                    lines.append(f"    ⚠️ Выше {verb} аналогов на {delta_vs_sold:.0f}%")

            ref_price = med_sold or med_active
            if ref_price:
                delta_pct = ((price_sqm - ref_price) / ref_price) * 100
                if delta_pct <= -10:
                    lines.append(f"    ✅ Ниже рынка на {abs(delta_pct):.0f}% — быстрая продажа")
                elif delta_pct <= 5:
                    lines.append(f"    ✅ В рынке ({delta_pct:+.0f}%)")
                elif delta_pct <= 20:
                    lines.append(f"    ⚠️ Выше рынка на {delta_pct:.0f}% — возможен торг")
                else:
                    lines.append(f"    ❌ Выше рынка на {delta_pct:.0f}% — высокий риск долгой экспозиции")
            lines.append("")

        # ▎3. Ликвидность
        if delta_pct > 20:
            adj_liq = max(1.0, liq - 2.0)
        elif delta_pct > 10:
            adj_liq = max(1.0, liq - 1.0)
        else:
            adj_liq = liq

        lines.append("<b>▎Ликвидность</b>")
        liq_label = "🟢 высокая" if adj_liq >= 7 else "🟡 средняя" if adj_liq >= 4 else "🔴 низкая"
        lines.append(f"    {adj_liq}/10 · {liq_label}")

        # Раскрытие — почему такой индекс
        reasons = []
        if area_grade:
            ag = area_grade.grade
            if ag in ("A+", "A"):
                reasons.append(f"✅ площадь востребована (грейд {ag})")
            elif ag == "B":
                reasons.append(f"➖ площадь средне востребована (грейд {ag})")
            else:
                reasons.append(f"❌ площадь мало востребована (грейд {ag})")
        ref_label = "проданных" if self._median_price_sqm(closed_comps) else "активных"
        if delta_pct > 50:
            reasons.append(f"❌ цена в 2+ раза выше {ref_label} аналогов (+{delta_pct:.0f}%)")
        elif delta_pct > 20:
            reasons.append(f"⚠️ цена значительно выше {ref_label} аналогов (+{delta_pct:.0f}%)")
        elif delta_pct > 5:
            reasons.append(f"➖ цена выше {ref_label} аналогов (+{delta_pct:.0f}%)")
        elif delta_pct >= -5:
            reasons.append("✅ цена в рынке")
        else:
            reasons.append(f"✅ цена ниже {ref_label} аналогов ({delta_pct:.0f}%)")
        for r in reasons:
            lines.append(f"    {r}")

        # Прогноз экспозиции
        if delta_pct <= -10:
            exp_text = "14–30 дней (ниже рынка — быстрый выход)"
        elif delta_pct <= 5:
            exp_text = "30–60 дней (цена в рынке)"
        elif delta_pct <= 20:
            exp_text = "60–120 дней (выше рынка, торг)"
        elif delta_pct <= 50:
            exp_text = "120–180 дней (значительно выше рынка)"
        else:
            exp_text = "180+ дней — продажа по текущей цене маловероятна"
        lines.append(f"    Прогноз: {exp_text}")

        # Конкуренция по району
        if district:
            active_dist = sum(1 for o in active if o.obj_type == canon and o.district == district)
            closed_dist = sum(1 for o in closed if o.obj_type == canon and o.district == district)
            if active_dist and closed_dist:
                ratio = round(active_dist / closed_dist, 1)
                verb = "сданных" if is_rent else "проданных"
                lines.append(f"    В районе: {active_dist} активных vs {closed_dist} {verb} ({ratio}:1)")
        lines.append("")

        # ▎4. Доходность и финансовая модель (только продажа)
        if not is_rent and price_val > 0:
            map_val = 0.0
            is_potential = False

            if is_gab and monthly_rent > 0:
                map_val = monthly_rent
            else:
                # Potential GAB: ищем рыночную ставку
                rent_objs = self._filter_objects(self._all_rent(), canon, district, area_val)
                med_rent_sqm = self._median_price_sqm(rent_objs)
                if med_rent_sqm and med_rent_sqm > 0:
                    map_val = med_rent_sqm * area_val
                    is_potential = True
                else:
                    # Дефолтные ставки по Тюмени на основе бенчмарков 2026
                    default_rates = {
                        "Офисное помещение": 1113.0,
                        "Торговое помещение": 1324.0,
                        "База/склад/производство": 685.0,
                        "Свободного назначения": 1170.0
                    }
                    rate = default_rates.get(canon, 1000.0)
                    map_val = rate * area_val
                    is_potential = True

            gpi = map_val * 12
            opex = gpi * 0.15  # 15% OPEX по умолчанию
            noi = gpi - opex
            cap_rate = (noi / price_val) * 100 if price_val > 0 else 0.0
            payback = price_val / noi if noi > 0 else 0.0

            # Справедливая цена для инвестора по типам ГАБ
            # Strong ГАБ (окупаемость 7-9 лет, в месяцах: ×120 - ×132)
            fair_strong_min = map_val * 120
            fair_strong_max = map_val * 132
            # Medium ГАБ (окупаемость 9-10 лет, в месяцах: ×108 - ×120)
            fair_medium_min = map_val * 108
            fair_medium_max = map_val * 120
            # Weak ГАБ (окупаемость 10-12 лет, в месяцах: ×84 - ×108)
            fair_weak_min = map_val * 84
            fair_weak_max = map_val * 108

            # Добавляем в lines метаданные для ИИ
            lines.append("<!-- GAB_FINANCIAL_CALCULATIONS")
            lines.append(f"MAP_VAL={map_val:.2f}")
            lines.append(f"IS_POTENTIAL={is_potential}")
            lines.append(f"GPI={gpi:.2f}")
            lines.append(f"OPEX={opex:.2f}")
            lines.append(f"NOI={noi:.2f}")
            lines.append(f"CAP_RATE={cap_rate:.2f}")
            lines.append(f"PAYBACK={payback:.2f}")
            lines.append(f"FAIR_STRONG_MIN={fair_strong_min:.2f}")
            lines.append(f"FAIR_STRONG_MAX={fair_strong_max:.2f}")
            lines.append(f"FAIR_MEDIUM_MIN={fair_medium_min:.2f}")
            lines.append(f"FAIR_MEDIUM_MAX={fair_medium_max:.2f}")
            lines.append(f"FAIR_WEAK_MIN={fair_weak_min:.2f}")
            lines.append(f"FAIR_WEAK_MAX={fair_weak_max:.2f}")
            lines.append("-->")

            # Резервный текстовый отчет
            title = "<b>▎Инвестиционная модель (ГАБ)</b>" if is_gab else "<b>▎Потенциал упаковки ГАБ</b>"
            lines.append(title)
            map_status = " (рыночный, расчетный)" if is_potential else " (фактический)"
            lines.append(f"    • Месячный арендный поток (МАП): {map_val:,.0f} ₽/мес{map_status}")
            lines.append(f"    • Валовой годовой доход (GPI): {gpi:,.0f} ₽/год")
            lines.append(f"    • Расходы и резервы (OPEX 15%): {opex:,.0f} ₽/год")
            lines.append(f"    • Чистый операционный доход (NOI): {noi:,.0f} ₽/год")
            lines.append(f"    • Доходность (Cap Rate): {cap_rate:.1f}% годовых")
            lines.append(f"    • Окупаемость: {payback:.1f} лет")
            lines.append("")

            lines.append("<b>▎Справедливая цена объекта для инвестора:</b>")
            lines.append(f"    • 🟢 Strong объект (окупаемость 7-9 лет): {fair_strong_min/1_000_000:.2f} – {fair_strong_max/1_000_000:.2f} млн ₽")
            lines.append(f"    • 🟡 Medium объект (окупаемость 9-10 лет): {fair_medium_min/1_000_000:.2f} – {fair_medium_max/1_000_000:.2f} млн ₽")
            lines.append(f"    • 🔴 Weak объект (окупаемость 10-12 лет): {fair_weak_min/1_000_000:.2f} – {fair_weak_max/1_000_000:.2f} млн ₽")
            lines.append("")

            # Анализ цены vs справедливой
            if price_val <= fair_strong_max:
                lines.append("    ✅ Объект находится в привлекательном инвестиционном коридоре (Strong ГАБ)")
            elif price_val <= fair_medium_max:
                lines.append("    🟡 Объект в рынке, окупаемость средняя (Medium ГАБ)")
            else:
                over_pct = round((price_val / fair_medium_max - 1) * 100) if fair_medium_max > 0 else 0
                lines.append(f"    ⚠️ Запрашиваемая цена завышена на {over_pct}% относительно рыночных ГАБ-метрик")
            lines.append("")

        # ▎Вердикт
        score = 0
        if area_grade and area_grade.grade in ("A+", "A"):
            score += 1
        if dist_grade and dist_grade.grade in ("A+", "A"):
            score += 1
        if adj_liq >= 7:
            score += 1
        if ref_price and price_sqm > 0 and delta_pct <= 10:
            score += 1

        lines.append("<b>▎Вердикт</b>")
        if score >= 3:
            lines.append("🟢 Объект ликвидный, цена в рынке")
            lines.append("    Рекомендация: можно выставлять")
        elif score >= 2:
            lines.append("🟡 Есть потенциал, но есть нюансы")
            lines.append("    Рекомендация: проверьте слабые стороны")
        else:
            lines.append("🔴 Высокие риски долгой экспозиции")
            lines.append("    Рекомендация: пересмотрите цену или стратегию")

        return "\n".join(lines)

    def _calc_liquidity(
        self,
        area_grade: AreaGrade | None,
        dist_grade: DistrictGrade | None,
        price_sqm: float,
        ref_price: float | None,
        benchmark: SegmentBenchmark | None,
    ) -> float:
        base = benchmark.liquidity_index if benchmark else 5.0

        if area_grade:
            if area_grade.grade in ("A+", "A"):
                base += 1.0
            elif area_grade.grade == "C":
                base -= 1.5

        if dist_grade:
            if dist_grade.rank <= 5:
                base += 1.0
            elif dist_grade.rank <= 10:
                base += 0.5
            elif dist_grade.rank > 20:
                base -= 1.0

        if ref_price and price_sqm > 0:
            delta = ((price_sqm - ref_price) / ref_price) * 100
            if delta <= -10:
                base += 0.7
            elif delta <= 5:
                base += 0.3
            elif delta >= 30:
                base -= 2.0
            elif delta >= 15:
                base -= 1.0

        return max(1.0, min(10.0, round(base, 1)))

    def analyze_from_text(self, text: str) -> str:
        """Fallback: распознать структуру из свободного текста."""
        if not text:
            return ""
        lower = text.lower()

        deal_type = ""
        if "сдать" in lower or "аренда" in lower:
            deal_type = "Сдать в аренду"
        elif "продажа" in lower or "продать" in lower:
            deal_type = "Продать"

        obj_type = ""
        if "офис" in lower:
            obj_type = "Офис"
        elif "торгов" in lower:
            obj_type = "Торговое помещение"
        elif "склад" in lower or "база" in lower:
            obj_type = "Склад/База"
        elif "псн" in lower or "свобод" in lower:
            obj_type = "Стрит-ритейл / ПСН"

        area_m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:м2|м²|кв)", lower)
        area = area_m.group(1) if area_m else ""

        price_m = re.search(r"(\d[\d\s]{4,})\s*(?:₽|руб)?", text)
        price = price_m.group(1) if price_m else ""

        if not deal_type or not obj_type or not area or not price:
            return ""
        return self.analyze(deal_type=deal_type, obj_type=obj_type, area=area, price=price, district="")

    def generate_chart(
        self,
        deal_type: str,
        obj_type: str,
        area: float,
        price: float,
        district: str,
    ) -> str | None:
        """Генерирует scatter-plot и возвращает путь к PNG файлу."""
        import tempfile
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib не установлен")
            return None

        canon = self.TYPE_ALIASES.get(obj_type, obj_type)
        is_rent = "аренд" in deal_type.lower() or "сдать" in deal_type.lower()
        price_sqm = round(price / area) if area > 0 else 0

        active = self._active_rent() if is_rent else self._active_sale()
        closed = self._closed_rent() if is_rent else self._closed_sale()

        active_f = self._filter_objects(active, canon, district, area, 0.5)
        closed_f = self._filter_objects(closed, canon, district, area, 0.5)
        if len(active_f) < 5:
            active_f = self._filter_objects(active, canon, None, area, 0.5)
        if len(closed_f) < 3:
            closed_f = self._filter_objects(closed, canon, None, area, 0.5)

        if not active_f and not closed_f:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")

        if active_f:
            ax.scatter(
                [o.area for o in active_f],
                [o.price_sqm for o in active_f],
                c="#4cc9f0", alpha=0.5, s=40, label=f"Активные ({len(active_f)})",
                edgecolors="none",
            )
        if closed_f:
            ax.scatter(
                [o.area for o in closed_f],
                [o.price_sqm for o in closed_f],
                c="#06d6a0", alpha=0.7, s=50, label=f"Закрытые ({len(closed_f)})",
                edgecolors="none",
            )

        ax.scatter(
            [area], [price_sqm],
            c="#ef233c", s=200, marker="*", zorder=5,
            label=f"Ваш объект ({price_sqm:,.0f} ₽/м²)",
            edgecolors="white", linewidths=0.5,
        )

        ax.set_xlabel("Площадь, м²", color="white", fontsize=11)
        price_unit = "₽/м²/мес" if is_rent else "₽/м²"
        ax.set_ylabel(f"Цена, {price_unit}", color="white", fontsize=11)
        ax.set_title(f"{canon} · {'Аренда' if is_rent else 'Продажа'} · {district or 'все районы'}",
                      color="white", fontsize=13, fontweight="bold")

        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("#333")
        ax.legend(facecolor="#16213e", edgecolor="#333", labelcolor="white", fontsize=9)
        ax.grid(True, alpha=0.15, color="white")

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="rbn_chart_")
        fig.savefig(tmp.name, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return tmp.name


market_analyzer = MarketAnalyzer()
