"""Deterministic investment calculator for commercial real estate."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from services.market_analyzer import market_analyzer


KEY_RATE = 14.5
DEPOSIT_RATE = 13.24
DEFAULT_EXPENSE_RATE = 0.15
CONTROL_RENT_RATE = 1000.0
TARGET_PAYBACK_YEARS = 9


@dataclass
class Scenario:
    name: str
    rent_rate: float
    map_value: float
    gross_income: float
    expenses: float
    noi: float
    yield_pct: float
    payback: float
    comment: str


def _to_float(value: object) -> float:
    text = str(value or "").lower().replace(" ", "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return 0.0
    num = float(m.group(1))
    if "млн" in text:
        num *= 1_000_000
    return num


def _money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽"


def _rate(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₽/м²"


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _years(value: float) -> str:
    if not value or value <= 0 or math.isinf(value):
        return "не окупается"
    return f"{value:.1f} лет"


def _scenario(name: str, area: float, price: float, rent_rate: float, comment: str) -> Scenario:
    map_value = area * rent_rate
    gross_income = map_value * 12
    expenses = gross_income * DEFAULT_EXPENSE_RATE
    noi = gross_income - expenses
    yield_pct = (noi / price) * 100 if price > 0 else 0
    payback = price / noi if noi > 0 else 0
    return Scenario(name, rent_rate, map_value, gross_income, expenses, noi, yield_pct, payback, comment)


def _required_rate_for_payback(area: float, price: float, years: int = TARGET_PAYBACK_YEARS) -> float:
    if area <= 0 or price <= 0:
        return 0.0
    required_noi = price / years
    required_gross = required_noi / (1 - DEFAULT_EXPENSE_RATE)
    required_map = required_gross / 12
    return required_map / area


def _required_indexation(start_noi: float, price: float, years: int = TARGET_PAYBACK_YEARS) -> float:
    """Annual indexation required for cumulative NOI to equal price in N years."""
    if start_noi <= 0 or price <= 0:
        return 0.0
    if start_noi * years >= price:
        return 0.0

    lo, hi = 0.0, 2.0
    for _ in range(80):
        mid = (lo + hi) / 2
        total = start_noi * (((1 + mid) ** years - 1) / mid) if mid else start_noi * years
        if total >= price:
            hi = mid
        else:
            lo = mid
    return hi * 100


def _linear_step(start_rate: float, area: float, price: float, years: int = TARGET_PAYBACK_YEARS) -> float:
    """Annual rub/m2 increase needed for cumulative NOI to equal price in N years."""
    denominator = area * 12 * (1 - DEFAULT_EXPENSE_RATE)
    if denominator <= 0:
        return 0.0
    required_sum_rates = price / denominator
    base_sum = years * start_rate
    steps_sum = years * (years - 1) / 2
    if steps_sum <= 0:
        return 0.0
    return max(0.0, (required_sum_rates - base_sum) / steps_sum)


def _cumulative_indexed_noi(start_noi: float, indexation_pct: float, years: int) -> float:
    total = 0.0
    for year in range(years):
        total += start_noi * ((1 + indexation_pct / 100) ** year)
    return total


def _market_rent_rate(obj_type: str, district: str, area: float) -> float:
    canon = market_analyzer.TYPE_ALIASES.get(obj_type, obj_type)
    rent_objs = market_analyzer._filter_objects(market_analyzer._all_rent(), canon, district, area)
    med_rent = market_analyzer._median_price_sqm(rent_objs)
    if med_rent and med_rent > 0:
        return float(med_rent)
    defaults = {
        "Офисное помещение": 1113.0,
        "Торговое помещение": 1324.0,
        "База/склад/производство": 685.0,
        "Свободного назначения": 1170.0,
    }
    return defaults.get(canon, CONTROL_RENT_RATE)


def _liquidity_block(deal_type: str, obj_type: str, area: float, price: float, district: str) -> tuple[float, str]:
    text = market_analyzer.analyze(
        deal_type=deal_type,
        obj_type=obj_type,
        area=str(area),
        price=str(price),
        district=district,
        is_gab=False,
    )
    score = 5.0
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*/10", text)
    if m:
        score = float(m.group(1).replace(",", "."))
    summary_lines = []
    capture = False
    for line in text.splitlines():
        plain = re.sub(r"<[^>]+>", "", line).strip()
        if plain.startswith("<!--"):
            break
        plain = re.sub(r"[🟢🟡🔴✅⚠️❌➖📊📍]", "", plain).strip()
        if "▎Ликвидность" in plain:
            capture = True
            continue
        if capture and plain.startswith("▎"):
            break
        if capture and plain:
            summary_lines.append(plain)
        if len(summary_lines) >= 5:
            break
    return score, "; ".join(summary_lines)


def build_investment_report(
    *,
    deal_type: str,
    obj_type: str,
    area: str,
    price: str,
    district: str,
    monthly_rent: float = 0,
) -> str:
    area_val = _to_float(area)
    price_val = _to_float(price)
    if area_val <= 0 or price_val <= 0:
        return "Не удалось рассчитать инвестиционную модель: нужна площадь и цена объекта."

    rent_rate_current = monthly_rent / area_val if monthly_rent and monthly_rent > 0 else 0.0
    market_rate = _market_rent_rate(obj_type, district, area_val)
    target_8_rate = _required_rate_for_payback(area_val, price_val, 8)
    target_9_rate = _required_rate_for_payback(area_val, price_val, 9)
    target_10_rate = _required_rate_for_payback(area_val, price_val, 10)
    deposit_rate_required = (price_val * (DEPOSIT_RATE / 100)) / (area_val * 12 * (1 - DEFAULT_EXPENSE_RATE))

    factual = None
    if rent_rate_current > 0:
        factual = _scenario("Факт сейчас", area_val, price_val, rent_rate_current, "фактический МАП из карточки")
    control = _scenario("Ставка 1000 ₽/м²", area_val, price_val, CONTROL_RENT_RATE, "обязательный расчет по ТЗ")
    market = _scenario("Рыночная модель", area_val, price_val, market_rate, "ориентир по рынку Тюмени 2026")
    target_8 = _scenario("Цель 8 лет", area_val, price_val, target_8_rate, "ставка для окупаемости 8 лет")
    target_9 = _scenario("Цель 9 лет", area_val, price_val, target_9_rate, "ставка для окупаемости 9 лет")
    target_10 = _scenario("Цель 10 лет", area_val, price_val, target_10_rate, "верхняя граница приемлемой окупаемости")
    deposit_target = _scenario("Доходность как депозит", area_val, price_val, deposit_rate_required, "уровень банковского депозита")
    downside_base = rent_rate_current if rent_rate_current > 0 else CONTROL_RENT_RATE
    downside = _scenario("Downside", area_val, price_val, downside_base * 0.85, "минус 15% к текущей/контрольной аренде")
    upside = _scenario("Upside", area_val, price_val, max(market_rate, CONTROL_RENT_RATE) * 1.07, "рынок/индексация")

    required_index = _required_indexation(control.noi, price_val)
    step_400 = _linear_step(400.0, area_val, price_val)
    step_500 = _linear_step(500.0, area_val, price_val)
    step_fact = _linear_step(rent_rate_current, area_val, price_val) if rent_rate_current > 0 else 0
    deposit_income_10 = price_val * (DEPOSIT_RATE / 100) * 10
    base_for_value = factual or control
    object_income_10 = base_for_value.noi * 10
    object_indexed_10 = _cumulative_indexed_noi(base_for_value.noi, 5.0, 10)
    fair_strong_min = base_for_value.map_value * 120
    fair_strong_max = base_for_value.map_value * 132
    fair_medium_min = base_for_value.map_value * 108
    fair_medium_max = base_for_value.map_value * 120
    fair_weak_min = base_for_value.map_value * 84
    fair_weak_max = base_for_value.map_value * 108
    fair_8 = base_for_value.noi * 8
    fair_9 = base_for_value.noi * 9
    fair_10 = base_for_value.noi * 10
    fair_deposit = base_for_value.noi / (DEPOSIT_RATE / 100)
    fair_key = base_for_value.noi / (KEY_RATE / 100)
    liq_score, liq_summary = _liquidity_block("продажа", obj_type, area_val, price_val, district)

    verdict = "покупать только при торге или росте аренды"
    decision_base = factual or control
    if decision_base.yield_pct >= KEY_RATE and decision_base.payback <= TARGET_PAYBACK_YEARS:
        verdict = "объект инвестиционно интересен"
    elif decision_base.yield_pct < DEPOSIT_RATE:
        verdict = "по текущей цене объект слабее депозита"

    scenarios = []
    if factual:
        scenarios.append(factual)
    scenarios.extend([control, market, target_9, deposit_target, downside, upside])

    def scenario_row(s: Scenario) -> str:
        return (
            f"{s.name} | {_rate(s.rent_rate)} | {_money(s.map_value)} | "
            f"{_money(s.noi)} | {_pct(s.yield_pct)} | {_years(s.payback)} | {s.comment}"
        )

    map_gap_9 = max(0.0, target_9.map_value - decision_base.map_value)
    map_gap_8 = max(0.0, target_8.map_value - decision_base.map_value)
    deposit_gap = max(0.0, deposit_target.map_value - decision_base.map_value)
    rent_rate_for_gap = rent_rate_current if rent_rate_current > 0 else CONTROL_RENT_RATE
    current_label = "фактическом МАП" if factual else "контрольной ставке 1000 ₽/м²"

    lines: list[str] = []
    lines.append("<b>Инвестиционный расчет коммерческого объекта</b>")
    lines.append("")
    
    # === САММЕРИ. КРАТКОЕ РЕЗЮМЕ ПРОЕКТА (EXECUTIVE SUMMARY) ===
    lines.append("<b>САММЕРИ. КРАТКОЕ РЕЗЮМЕ ПРОЕКТА (EXECUTIVE SUMMARY)</b>")
    lines.append("Краткая выжимка ключевых показателей и стратегий переупаковки для быстрого ознакомления с инвестиционным потенциалом объекта:")
    lines.append("")
    lines.append("<b>1. Краткий инвестиционный вердикт</b>")
    lines.append(
        f"Объект: {obj_type}, {area_val:.1f} м², {district or 'район не указан'}, цена {_money(price_val)}. "
        f"При {current_label} чистый доход объекта = {_money(decision_base.noi)} в год, "
        f"доходность = {_pct(decision_base.yield_pct)}, окупаемость = {_years(decision_base.payback)}. "
        f"Вывод: {verdict}."
    )
    if decision_base.payback > 10:
        lines.append(
            f"Текущий денежный поток не окупает объект за 9-10 лет. Для 9 лет нужен МАП "
            f"{_money(target_9.map_value)}, то есть +{_money(map_gap_9)} к текущему уровню."
        )
    lines.append("")
    
    lines.append("<b>2. Сводное сравнение стратегий переупаковки</b>")
    rate_b = market_rate * 1.35
    map_b = rate_b * area_val
    noi_b = map_b * 12 * (1 - DEFAULT_EXPENSE_RATE)
    payback_b = price_val / noi_b
    fair_9_b = noi_b * 9
    lines.append("Стратегия | Ставка аренды | Месячный доход (МАП) | Окупаемость объекта | Стоимость как бизнеса")
    lines.append(f"Текущее состояние | {_rate(rent_rate_for_gap)} | {_money(decision_base.map_value)} | {_years(decision_base.payback)} | {_money(decision_base.noi * 9)}")
    lines.append(f"Вариант А: ГАБ | {_rate(market_rate)} | {_money(market.map_value)} | {_years(market.payback)} | {_money(market.noi * 9)}")
    lines.append(f"Вариант Б: Деление | {_rate(rate_b)} | {_money(map_b)} | {_years(payback_b)} | {_money(fair_9_b)}")
    lines.append("")

    # === ЧАСТЬ 1. ДЕТАЛЬНЫЙ ИНВЕСТИЦИОННЫЙ АНАЛИЗ ===
    lines.append("<b>ЧАСТЬ 1. ДЕТАЛЬНЫЙ ИНВЕСТИЦИОННЫЙ АНАЛИЗ</b>")
    lines.append("")

    lines.append("<b>2. Исходные данные и допущения</b>")
    lines.append("Показатель | Значение")
    lines.append(f"Площадь | {area_val:.1f} м²")
    lines.append(f"Цена объекта | {_money(price_val)}")
    lines.append(f"Цена за м² | {_money(price_val / area_val)}")
    if factual:
        lines.append(f"Фактический МАП | {_money(factual.map_value)}")
        lines.append(f"Фактическая ставка | {_rate(factual.rent_rate)}")
    lines.append("Контрольная ставка | 1000 ₽/м²")
    lines.append(f"Рыночный ориентир аренды | {_rate(market_rate)}")
    lines.append("Расходы на содержание объекта | 15% от валового годового дохода (допущение)")
    lines.append(f"Ключевая ставка ЦБ РФ | {_pct(KEY_RATE)}")
    lines.append(f"Ориентир по депозитам | {_pct(DEPOSIT_RATE)}")
    lines.append("")

    lines.append("<b>3. Финансовая модель</b>")
    lines.append("Показатель | Формула | Значение")
    lines.append(f"МАП | площадь × ставка | {_money(decision_base.map_value)}")
    lines.append(f"Валовый годовой доход | МАП × 12 | {_money(decision_base.gross_income)}")
    lines.append(f"Расходы на содержание | валовый доход × 15% | {_money(decision_base.expenses)}")
    lines.append(f"Чистый доход объекта | валовый доход − расходы | {_money(decision_base.noi)}")
    lines.append(f"Доходность объекта | чистый доход ÷ цена | {_pct(decision_base.yield_pct)}")
    lines.append(f"Окупаемость | цена ÷ чистый доход | {_years(decision_base.payback)}")
    lines.append("")

    lines.append("<b>4. Обязательные расчеты калькулятора</b>")
    lines.append("Вопрос | Ответ")
    if factual:
        lines.append(f"Окупаемость при фактическом МАП | {_years(factual.payback)}")
    lines.append(f"Окупаемость при 1000 ₽/м² и текущей цене | {_years(control.payback)}")
    lines.append(f"Какая ставка нужна для окупаемости 10 лет | {_rate(target_10_rate)} / МАП {_money(target_10.map_value)}")
    lines.append(f"Какая ставка нужна для окупаемости 9 лет | {_rate(target_9_rate)} / МАП {_money(target_9.map_value)}")
    lines.append(f"Какая ставка нужна для окупаемости 8 лет | {_rate(target_8_rate)} / МАП {_money(target_8.map_value)}")
    lines.append(f"Какая ставка нужна, чтобы конкурировать с депозитом | {_rate(deposit_rate_required)} / МАП {_money(deposit_target.map_value)}")
    if required_index <= 0:
        lines.append("Какая индексация нужна при 1000 ₽/м² для 9 лет | 0%, объект уже укладывается in 9 лет")
    else:
        lines.append(f"Какая индексация нужна при 1000 ₽/м² для 9 лет | {_pct(required_index)} в год")
    lines.append(f"Старт 400 ₽/м²: ежегодное повышение для 9 лет | +{_rate(step_400)} каждый год")
    lines.append(f"Старт 500 ₽/м²: ежегодное повышение для 9 лет | +{_rate(step_500)} каждый год")
    if factual:
        lines.append(f"Старт с текущей ставки {_rate(rent_rate_for_gap)}: ежегодное повышение для 9 лет | +{_rate(step_fact)} каждый год")
    lines.append("")

    lines.append("<b>5. Что делать, если текущий МАП не окупает 9-10 лет</b>")
    lines.append("Рычаг | Что нужно сделать | Инвестиционный смысл")
    lines.append(
        f"Поднять аренду до 9 лет | МАП {_money(target_9.map_value)} "
        f"(+{_money(map_gap_9)} к текущему уровню) | объект начинает окупаться за 9 лет"
    )
    lines.append(
        f"Поднять аренду до 8 лет | МАП {_money(target_8.map_value)} "
        f"(+{_money(map_gap_8)} к текущему уровню) | объект становится заметно интереснее инвестору"
    )
    lines.append(
        f"Догнать депозит | МАП {_money(deposit_target.map_value)} "
        f"(+{_money(deposit_gap)} к текущему уровню) | доходность сопоставима с банковским инструментом"
    )
    lines.append(
        f"Торг по цене | цена для 9 лет при текущем доходе около {_money(fair_9)} | "
        "если аренду поднять нельзя, должна снижаться цена"
    )
    lines.append("Если ни МАП, ни цена не меняются, объект нельзя упаковывать как сильную инвестицию: это покупка под собственное пользование или спекуляция на росте стоимости.")
    lines.append("")

    lines.append("<b>6. Сценарный анализ</b>")
    lines.append("Сценарий | Ставка | МАП | Чистый доход | Доходность | Окупаемость | Comment")
    for s in scenarios:
        lines.append(scenario_row(s))
    lines.append("")

    lines.append("<b>7. Сравнение с рынком и депозитом</b>")
    lines.append("Инструмент | Доходность | Вывод")
    lines.append(f"Ключевая ставка ЦБ РФ | {_pct(KEY_RATE)} | безрисковый ориентир денег")
    lines.append(f"Депозитный ориентир | {_pct(DEPOSIT_RATE)} | конкурирует с объектом без риска вакантности")
    if factual:
        lines.append(f"Объект по фактическому МАП | {_pct(factual.yield_pct)} | {'выше депозита' if factual.yield_pct > DEPOSIT_RATE else 'ниже депозита'}")
    lines.append(f"Объект при 1000 ₽/м² | {_pct(control.yield_pct)} | {'выше депозита' if control.yield_pct > DEPOSIT_RATE else 'ниже депозита'}")
    lines.append(f"Объект при ставке для 9 лет | {_pct(target_9.yield_pct)} | целевая окупаемость, но не всегда выше депозита")
    lines.append(f"Объект на уровне депозита | {_pct(deposit_target.yield_pct)} | ставка аренды должна быть {_rate(deposit_rate_required)}")
    lines.append("")

    lines.append("<b>8. Доход за 10 лет</b>")
    lines.append("Инструмент | Формула | Доход за 10 лет")
    lines.append(f"Депозит | цена × {DEPOSIT_RATE}% × 10 | {_money(deposit_income_10)}")
    lines.append(f"Объект по текущему доходу | чистый доход × 10 | {_money(object_income_10)}")
    lines.append(f"Объект с индексацией 5% | сумма чистого дохода 10 лет | {_money(object_indexed_10)}")
    lines.append("")

    lines.append("<b>9. Справедливая цена для инвестора</b>")
    lines.append("Метод | Цена")
    lines.append(f"Цена для окупаемости 8 лет по текущему доходу | {_money(fair_8)}")
    lines.append(f"Цена для окупаемости 9 лет по текущему доходу | {_money(fair_9)}")
    lines.append(f"Цена для окупаемости 10 лет по текущему доходу | {_money(fair_10)}")
    lines.append(f"Strong по МАП ×120-132 | {_money(fair_strong_min)} - {_money(fair_strong_max)}")
    lines.append(f"Medium по МАП ×108-120 | {_money(fair_medium_min)} - {_money(fair_medium_max)}")
    lines.append(f"Weak по МАП ×84-108 | {_money(fair_weak_min)} - {_money(fair_weak_max)}")
    lines.append(f"По депозитной доходности {DEPOSIT_RATE}% | {_money(fair_deposit)}")
    lines.append(f"По ключевой ставке {KEY_RATE}% | {_money(fair_key)}")
    lines.append("")

    lines.append("<b>10. Ликвидность</b>")
    lines.append(f"Оценка ликвидности: {liq_score:.1f}/10.")
    if liq_summary:
        lines.append(liq_summary)
    lines.append("Ликвидность ухудшают: завышенная цена, слабый арендный поток, отсутствие арендатора, слабая видимость, риск долгой вакантности.")
    lines.append("")

    lines.append("<b>11. Ступенчатая модель аренды для окупаемости 9 лет</b>")
    lines.append("Это не прогноз рынка, а математический план: какой рост аренды нужен, чтобы накопленный чистый доход за 9 лет вернул цену объекта.")
    lines.append("Год | Старт 500 ₽/м² | МАП | Чистый доход | Накопленный доход")
    total_500 = 0.0
    for year in range(1, TARGET_PAYBACK_YEARS + 1):
        rate_500 = 500 + step_500 * (year - 1)
        map_500 = rate_500 * area_val
        noi_500 = map_500 * 12 * (1 - DEFAULT_EXPENSE_RATE)
        total_500 += noi_500
        lines.append(f"{year} | {_rate(rate_500)} | {_money(map_500)} | {_money(noi_500)} | {_money(total_500)}")
    if factual:
        lines.append("")
        lines.append(f"План от фактической ставки {_rate(rent_rate_current)}")
        lines.append("Год | Ставка | МАП | Чистый доход | Накопленный доход")
        total_fact = 0.0
        for year in range(1, TARGET_PAYBACK_YEARS + 1):
            rate_fact = rent_rate_current + step_fact * (year - 1)
            map_fact = rate_fact * area_val
            noi_fact = map_fact * 12 * (1 - DEFAULT_EXPENSE_RATE)
            total_fact += noi_fact
            lines.append(f"{year} | {_rate(rate_fact)} | {_money(map_fact)} | {_money(noi_fact)} | {_money(total_fact)}")
    lines.append(
        f"Ключевой вывод: к 9-летней окупаемости приводит не стартовая ставка, а средний МАП за период. "
        f"Для этого объекта средняя ставка за 9 лет должна быть около {_rate(target_9_rate)}."
    )
    lines.append("")

    lines.append("<b>12. Как увеличить стоимость объекта</b>")
    lines.append(f"- Довести МАП минимум до {_money(target_9.map_value)} для окупаемости 9 лет или до {_money(target_8.map_value)} для 8 лет.")
    lines.append(f"- Если текущий МАП сохранить, цена для 9-летней окупаемости около {_money(fair_9)}.")
    lines.append("- Зафиксировать договор аренды на 3-7 лет и индексацию 5-7% в год.")
    lines.append("- Переложить часть расходов на содержание объекта на арендатора.")
    lines.append("- Посадить надежного арендатора и упаковать объект как ГАБ.")
    lines.append("- Улучшить входную группу, витрины, навигацию, ремонт под арендатора.")
    lines.append("")

    lines.append("<b>13. Итоговый инвестиционный вывод</b>")
    lines.append("Если текущий МАП не окупает объект за 9-10 лет, есть только три честных варианта: снизить цену, поднять чистый доход или продавать объект не как сильный ГАБ, а как помещение с потенциалом.")
    lines.append(f"Инвестор купит объект по текущей цене, если МАП будет доведен минимум до {_money(target_9.map_value)} и договор аренды будет надежным.")
    lines.append(f"Если МАП остается около {_money(decision_base.map_value)}, инвестиционная цена для 9 лет около {_money(fair_9)}, а не {_money(price_val)}.")
    lines.append(f"Ключевое условие сделки: ставка аренды около {_rate(target_9_rate)} или цена не выше уровня, который подтверждается текущим денежным потоком.")
    lines.append("")
    lines.append("Главный принцип: инвестор покупает не помещение, а денежный поток и риск этого потока.")
    lines.append("")

    # === ЧАСТЬ 2. ВАРИАНТЫ ПЕРЕУПАКОВКИ ОБЪЕКТА ДЛЯ СОБСТВЕННИКА ===
    lines.append("<b>ЧАСТЬ 2. ВАРИАНТЫ ПЕРЕУПАКОВКИ ДЛЯ СОБСТВЕННИКА</b>")
    lines.append("Для повышения привлекательности объекта и сокращения срока окупаемости до рыночных стандартов рекомендуется рассмотреть два сценария переупаковки:")
    lines.append("")
    lines.append("<b>14. Вариант А: Упаковка в Готовый Арендный Бизнес (ГАБ)</b>")
    lines.append("Суть: привлечение стабильного сетевого арендатора (федеральный ритейл, супермаркет, аптечная сеть, пункт выдачи заказов) с долгосрочным зарегистрированным договором аренды.")
    lines.append(f"- Целевая рыночная ставка аренды: {_rate(market_rate)}")
    lines.append(f"- Ожидаемый ежемесячный доход (МАП): {_money(market.map_value)}")
    lines.append(f"- Окупаемость объекта по текущей цене снизится до {_years(market.payback)} (вместо {_years(decision_base.payback)}).")
    lines.append(f"- Ценность объекта как ГАБ для инвесторов составит около {_money(market.noi * 9)} (окупаемость 9 лет).")
    lines.append("")
    lines.append("<b>15. Вариант Б: Деление площади на мелкие блоки (Редевелопмент)</b>")
    lines.append("Суть: нарезка помещения на 3-4 независимых мини-офиса или торговых блока с отдельными входами/мокрыми точками. Ставка на мелкий формат всегда выше среднерыночной на 35%. Это также диверсифицирует риски простоя.")
    rate_b = market_rate * 1.35
    map_b = rate_b * area_val
    noi_b = map_b * 12 * (1 - DEFAULT_EXPENSE_RATE)
    payback_b = price_val / noi_b
    fair_9_b = noi_b * 9
    lines.append(f"- Целевая ставка аренды мелких блоков: {_rate(rate_b)} (+35% к рынку)")
    lines.append(f"- Суммарный ежемесячный доход (МАП): {_money(map_b)}")
    lines.append(f"- Стоимость объекта после редевелопмента возрастет до {_money(fair_9_b)}.")
    lines.append("")

    return "\n".join(lines)
