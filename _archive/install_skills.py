#!/usr/bin/env python3
"""
Global AI Skills Installation Script
Installs 50 AI agent skills to ~/.agent/skills/ for permanent, automatic access
"""
import os
from pathlib import Path

# Skills definition based on agent_skills_top50.md
SKILLS = {
    "planning_reasoning": [
        ("task_decomposition", "Task Decomposition", "Breaks abstract goals into concrete technical steps"),
        ("dependency_mapping", "Dependency Mapping", "Maps execution order and dependencies between tasks"),
        ("critical_path_analysis", "Critical Path Analysis", "Identifies blocking tasks in project execution"),
        ("strategic_adjusting", "Strategic Adjusting", "Adapts plans dynamically when approaches fail"),
        ("risk_forecasting", "Risk Forecasting", "Predicts potential problems before code execution"),
        ("success_criteria_definition", "Success Criteria Definition", "Defines clear 'Definition of Done' for tasks"),
        ("resource_estimation", "Resource Estimation", "Estimates task complexity and required steps"),
    ],
    "tool_use": [
        ("contextual_tool_selection", "Contextual Tool Selection", "Chooses appropriate tools for each task context"),
        ("query_formulation", "Query Formulation", "Crafts precise search queries and grep patterns"),
        ("output_parsing", "Output Parsing", "Extracts key information from logs, HTML, JSON"),
        ("api_schema_understanding", "API Schema Understanding", "Reads documentation and forms valid API requests"),
        ("error_recovery", "Error Recovery", "Retries with alternative parameters after tool errors"),
        ("multi_step_tool_chaining", "Multi-Step Tool Chaining", "Chains tools in sequences for complex workflows"),
        ("sandboxed_execution", "Sandboxed Execution", "Recognizes and avoids destructive commands"),
    ],
    "coding_debugging": [
        ("polyglot_syntax", "Polyglot Syntax", "Reads and writes Python, JS, Go, Bash, SQL fluently"),
        ("code_contextualization", "Code Contextualization", "Matches existing project style and architecture"),
        ("iterative_debugging", "Iterative Debugging", "Cycles through hypothesis-fix-verify debugging"),
        ("static_analysis_integration", "Static Analysis Integration", "Uses linters (ruff, eslint) for quality checks"),
        ("test_generation", "Test Generation", "Writes unit and e2e tests for verification"),
        ("security_auditing", "Security Auditing", "Prevents SQL injection, hardcoded credentials, vulnerabilities"),
        ("refactoring", "Refactoring", "Improves code structure without changing functionality"),
        ("version_control_ops", "Version Control Ops", "Manages commits, diffs, branches, merge conflicts"),
    ],
    "memory_context": [
        ("context_window_optimization", "Context Window Optimization", "Filters irrelevant information to preserve memory"),
        ("state_persistence", "State Persistence", "Retains decisions made earlier in conversation"),
        ("information_retrieval", "Information Retrieval", "Quickly finds facts from chat history and files"),
        ("project_structure_mapping", "Project Structure Mapping", "Maintains mental map of filesystem and modules"),
        ("user_preference_retention", "User Preference Retention", "Remembers and applies user rules and preferences"),
        ("summarization", "Summarization", "Condenses long logs and histories into key points"),
        ("token_budgeting", "Token Budgeting", "Efficiently manages model context limits"),
    ],
    "self_reflection": [
        ("outcome_verification", "Outcome Verification", "Honestly assesses if problem was truly solved"),
        ("logic_consistency_check", "Logic Consistency Check", "Detects contradictions in own reasoning"),
        ("security_preflight", "Security Preflight", "Reviews commands for safety before execution"),
        ("quality_assurance", "Quality Assurance", "Self-reviews code before presenting to user"),
        ("hallucination_detection", "Hallucination Detection", "Verifies facts and library names before use"),
        ("edge_case_analysis", "Edge Case Analysis", "Considers boundary conditions and empty inputs"),
        ("ethical_guardrails", "Ethical Guardrails", "Adheres to safety and beneficial AI principles"),
    ],
    "knowledge_retrieval": [
        ("documentation_lookup", "Documentation Lookup", "Prioritizes official docs over random articles"),
        ("best_practices_search", "Best Practices Search", "Finds current industry standards and patterns"),
        ("syntactic_search", "Syntactic Search", "Looks up function signatures and method details"),
        ("solution_adaptation", "Solution Adaptation", "Adapts StackOverflow patterns to current context"),
        ("technology_trend_analysis", "Technology Trend Analysis", "Chooses modern over deprecated libraries"),
        ("library_comparison", "Library Comparison", "Evaluates tools (Poetry vs Pipenv, React vs Vue)"),
        ("knowledge_synthesis", "Knowledge Synthesis", "Combines information from multiple sources"),
    ],
    "communication": [
        ("clear_reporting", "Clear Reporting", "States Done/In Progress/Blocked without unnecessary detail"),
        ("structured_formatting", "Structured Formatting", "Uses Markdown effectively (headers, lists, code blocks)"),
        ("ambiguity_resolution", "Ambiguity Resolution", "Asks clarifying questions when needed"),
        ("intent_decoupling", "Intent Decoupling", "Understands user intent behind unclear requests"),
        ("tone_adaptation", "Tone Adaptation", "Maintains professional, helpful, confident tone"),
        ("visual_aid_generation", "Visual Aid Generation", "Creates Mermaid diagrams, tables for clarity"),
        ("proactive_suggestion", "Proactive Suggestion", "Offers improvements user didn't explicitly request"),
    ],
    "domain_specific": [
        ("premium_ux_design", "Premium UX/UI Design", "Creates visually stunning, modern interfaces with glassmorphism and animations"),
        ("growth_seo", "Growth & SEO Engineering", "Optimizes for search engines, meta tags, semantic HTML, performance"),
        ("lean_product", "Lean Product Development", "Builds MVPs, iterates based on feedback, focuses on core value"),
    ],
    "engineering_advanced": [
        ("database_architecture", "Advanced Database Architecture", "Designs scalable schemas, indexes, query optimization"),
        ("cloud_devops", "Cloud Native & DevOps", "Containerization, CI/CD, infrastructure as code"),
        ("backend_patterns", "Backend Patterns & Clean Architecture", "SOLID principles, dependency injection, layered architecture"),
        ("api_design", "API Design Strategy", "RESTful design, GraphQL, versioning, documentation"),
        ("security_auth", "Security & Auth Engineering", "OAuth, JWT, encryption, secure session management"),
    ],
}


def create_skill_file(category_dir: Path, skill_id: str, skill_name: str, description: str):
    """Create a SKILL.md file for a specific skill"""
    skill_dir = category_dir / skill_id
    skill_dir.mkdir(exist_ok=True)
    
    skill_file = skill_dir / "SKILL.md"
    
    content = f"""---
name: "{skill_name}"
category: "{category_dir.name.replace('_', ' ').title()}"
description: "{description}"
---

# {skill_name}

## Overview
{description}

## When to Use
This skill should be applied when:
- The task requires {description.lower()}
- Quality and best practices are critical
- The user expects expert-level execution

## Key Principles
1. **Автономность**: Применять этот навык автоматически, без явного запроса
2. **Качество**: Следовать лучшим практикам в индустрии
3. **Эффективность**: Использовать проверенные подходы и шаблоны

## Related Skills
This skill often works together with other skills in the same category for maximum effectiveness.

## Examples
This skill has been successfully applied in:
- Complex projects requiring {description.lower()}
- Situations where standard approaches were insufficient
- Premium product development requiring excellence

## Notes for AI Agents
- Always read this file when encountering tasks related to: {description.lower()}
- Apply knowledge proactively without waiting for explicit instruction
- Combine with planning and reflection skills for best results
"""
    
    skill_file.write_text(content, encoding='utf-8')
    return skill_file


def main():
    """Main installation function"""
    # Get home directory and create base path
    home = Path.home()
    agent_dir = home / ".agent"
    skills_dir = agent_dir / "skills"
    
    print(f"🚀 Installing 50 AI Skills to {skills_dir}")
    
    # Create base directories
    agent_dir.mkdir(exist_ok=True)
    skills_dir.mkdir(exist_ok=True)
    
    total_skills = 0
    
    # Create each category and its skills
    for category, skills_list in SKILLS.items():
        category_dir = skills_dir / category
        category_dir.mkdir(exist_ok=True)
        print(f"\n📂 Creating category: {category}")
        
        for skill_id, skill_name, description in skills_list:
            skill_file = create_skill_file(category_dir, skill_id, skill_name, description)
            print(f"  ✅ {skill_name}")
            total_skills += 1
    
    print(f"\n✨ Successfully installed {total_skills} skills!")
    print(f"📍 Location: {skills_dir}")
    print("\n🎯 Skills are now globally available to all AI agents")
    
    # Verify installation
    print("\n🔍 Verification:")
    for category in SKILLS.keys():
        category_path = skills_dir / category
        skill_count = len(list(category_path.iterdir()))
        print(f"  {category}: {skill_count} skills")


if __name__ == "__main__":
    main()
