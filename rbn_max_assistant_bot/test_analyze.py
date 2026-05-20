from services.market_analyzer import market_analyzer
print("docs_dir:", market_analyzer.docs_dir)
print("exists:", (market_analyzer.docs_dir / "RBN_DEMAND_GRADES.csv").exists())
