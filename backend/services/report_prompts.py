"""Claude prompts for SIWES report generation. School-config-aware: the
SYSTEM_REPORT string is built dynamically per school instead of hardcoded
to Landmark University Mechatronics."""

from typing import Any


def system_prompt(school_config: dict | None = None) -> str:
    cfg = school_config or {}
    name = cfg.get("name", "a Nigerian")
    return (
        f"You are a professional academic writer producing a Nigerian undergraduate SIWES "
        f"(Student Industrial Work Experience Scheme) report for a {name} "
        f"student. Write in formal British English, in the first person past tense where "
        f"appropriate. Use clear, declarative sentences. Do not invent facts that contradict "
        f"the supplied context. Output plain prose only unless a JSON schema is explicitly requested."
    )


# Back-compat alias for any caller importing SYSTEM_REPORT directly
SYSTEM_REPORT = system_prompt(None)


def chapter_one_prompt(payload: dict) -> str:
    company = payload["internship"]["company_name"]
    department_at_company = payload["internship"]["department_at_company"]
    company_history = payload["content"].get("company_history", "")
    return (
        "Generate the prose content for Chapter One of a SIWES report. Return a JSON object "
        "with EXACTLY these keys. Where a value is a 'paragraph array', it MUST be a JSON "
        "array of strings, one string per paragraph — never multiple unkeyed entries.\n\n"
        "  intro                          — paragraph array of 3 substantial paragraphs introducing the report\n"
        "  background_itf                 — paragraph array of 4 paragraphs on the Industrial Training Fund "
        "                                   (history, mandate, funding model, regulatory role)\n"
        "  core_objectives_itf            — JSON array of 6 to 8 short bullet strings, each one full sentence\n"
        "  historical_background_siwes    — paragraph array of 5 paragraphs on SIWES history in Nigeria\n"
        "  aim_of_siwes                   — paragraph array of 2 paragraphs\n"
        "  objectives_of_siwes            — JSON array of EXACTLY 5 short noun-phrase bullet strings "
        "                                   (these are the canonical ITF objectives — keep at 5)\n"
        "  company_profile                — paragraph array of 3 paragraphs describing the company\n"
        "  brief_history                  — paragraph array of 4 to 5 paragraphs of the company's history\n"
        "  organisational_structure_intro — paragraph array of 2 paragraphs introducing the organisational structure\n"
        "  departments                    — JSON array of 9 to 12 objects { name, description } describing "
        "                                   typical departments. Each description is a single string of "
        "                                   3 to 5 sentences.\n\n"
        f"Company: {company}\n"
        f"Department attached: {department_at_company}\n"
        f"User-supplied company history (use as ground truth, expand on it): {company_history}\n\n"
        "Return ONLY the JSON object."
    )


def chapter_two_prompt(payload: dict) -> str:
    tools = payload["content"].get("tools_used", [])
    weeks = payload["content"].get("weekly_activities", [])
    company = payload["internship"]["company_name"]
    department_at_company = payload["internship"]["department_at_company"]
    weeks_block = "\n".join(f"- Week {w.get('week', i+1)}: {w.get('summary', '')}" for i, w in enumerate(weeks))
    tools_block = ", ".join(tools)
    return (
        "Generate the prose content for Chapter Two (WORKDONE) of a SIWES report. "
        "Return a JSON object with EXACTLY these keys. Where a value is a 'paragraph array', "
        "it MUST be a JSON array of strings, one string per paragraph.\n\n"
        "  intro                  — paragraph array of 2 substantial paragraphs for the chapter\n"
        "  tools_intro            — paragraph array of 2 paragraphs introducing section 2.1 "
        "                           'Basic Tools, Instruments, and Equipment Used'\n"
        "  hand_tools             — JSON array of 6 to 8 objects { name, description } drawn from the tools list. "
        "                           Each description is a single string of 4 to 6 sentences.\n"
        "  measuring_instruments  — JSON array of 5 to 7 objects { name, description }. "
        "                           Each description is a single string of 4 to 6 sentences.\n"
        "  specialised_equipment  — JSON array of 5 to 7 objects { name, description }. "
        "                           Each description is a single string of 4 to 6 sentences.\n"
        "  themes                 — JSON array of 6 to 10 thematic activity sections. Each is an object "
        "                           { title, paragraphs } where title is an UPPER CASE thematic heading "
        "                           (e.g. 'SAFETY INDUCTION', 'PLC PROGRAMMING') and paragraphs is a "
        "                           paragraph array of 4 to 6 strings covering weekly activities under that "
        "                           theme. Cover all the weeks; weave week numbers into prose naturally.\n\n"
        f"Company: {company}\n"
        f"Department attached: {department_at_company}\n"
        f"Tools list: {tools_block}\n"
        f"Weekly activities:\n{weeks_block}\n\n"
        "Return ONLY the JSON object."
    )


def chapter_three_prompt(payload: dict) -> str:
    challenges = payload["content"].get("challenges", [])
    problems_solved = payload["content"].get("problems_solved", [])
    skills = payload["content"].get("skills_acquired", "")
    weeks = payload["content"].get("weekly_activities", [])
    weeks_block = "\n".join(f"- Week {w.get('week', i+1)}: {w.get('summary', '')}" for i, w in enumerate(weeks))
    ch_block = "\n".join(f"- Problem: {c.get('problem', '')} | Solution: {c.get('solution', '')}" for c in challenges)
    ps_block = "\n".join(f"- {p.get('title', '')}: {p.get('narrative', '')}" for p in problems_solved)
    return (
        "Generate Chapter Three (Challenges Encountered and Problems Solved). "
        "Return a JSON object with EXACTLY these keys. Where a value is a 'paragraph array', "
        "it MUST be a JSON array of strings.\n\n"
        "  intro_3_1     — paragraph array of 2 paragraphs introducing the table of problems encountered\n"
        "  table_rows    — JSON array of up to 10 objects { problem, solution }; refine and tighten "
        "                  the user-supplied challenges, each cell 1 to 2 sentences\n"
        "  intro_3_2     — paragraph array of 2 paragraphs introducing the narrative of problems solved\n"
        "  solved_items  — JSON array of 6 to 8 objects { title, paragraph }, each title a short "
        "                  noun-phrase (Title Case), each paragraph a single string of 5 to 7 sentences "
        "                  in first person past tense\n"
        "  closing       — paragraph array of 2 paragraphs reflecting on what the problem solving taught\n\n"
        f"User-supplied challenges:\n{ch_block}\n\n"
        f"User-supplied problems_solved (use these where present; infer additional items from weekly "
        f"activities if the list is sparse):\n{ps_block or '[none — please infer all from context]'}\n\n"
        f"Skills acquired (for context): {skills}\n"
        f"Weekly activities (for context):\n{weeks_block}\n\n"
        "Return ONLY the JSON object."
    )


def chapter_four_prompt(payload: dict) -> str:
    skills = payload["content"].get("skills_acquired", "")
    recommendations = payload["content"].get("recommendations", "")
    company = payload["internship"]["company_name"]
    duration = payload["internship"]["duration"]
    return (
        "Generate Chapter Four (Summary, Conclusion and Recommendation). "
        "Return a JSON object with EXACTLY these keys.\n\n"
        "  summary         — paragraph array of 4 to 5 paragraphs summarising the entire SIWES experience\n"
        "  conclusion      — paragraph array of 3 paragraphs reflecting on the value of the training\n"
        "  recommendations — JSON array of 6 to 9 short recommendation strings (one per bullet, "
        "                     addressed to students, institutions, organisations or government). Use the "
        "                     user-supplied recommendations as ground truth and refine into formal "
        "                     academic prose.\n\n"
        f"Company: {company}\nDuration: {duration}\n"
        f"Skills acquired: {skills}\n"
        f"User-supplied recommendations: {recommendations}\n\n"
        "Return ONLY the JSON object."
    )


def acknowledgement_prompt(payload: dict) -> str:
    student = payload["student"]["name"]
    industry = payload["internship"].get("industry_supervisor_name", "")
    academic = payload["internship"].get("academic_supervisor_name", "")
    department = payload["student"]["department"]
    return (
        "Write the Acknowledgement page for a SIWES report. Return a single string of "
        "2 to 3 short paragraphs separated by blank lines (no headings). Acknowledge: God, "
        "the industry-based supervisor by name, the academic supervisor by name, and the "
        "lecturers of the named department. Warm, formal, first person.\n\n"
        f"Student: {student}\n"
        f"Industry supervisor: {industry}\n"
        f"Academic supervisor: {academic}\n"
        f"Department: {department}\n\n"
        "Return ONLY the paragraphs, no preamble."
    )


def abstract_prompt(payload: dict, chapter_summaries: dict) -> str:
    return (
        "Write the Abstract for a SIWES report. Return ONE paragraph of 6 to 9 sentences. "
        "State: the purpose of SIWES, where the training was undertaken, the department, the "
        "broad areas covered, and a one-sentence overall outcome. Formal, third person.\n\n"
        f"Company: {payload['internship']['company_name']}\n"
        f"Department at company: {payload['internship']['department_at_company']}\n"
        f"Duration: {payload['internship']['duration']}\n"
        f"Chapter 2 themes covered: {chapter_summaries.get('ch2_themes', '')}\n"
        f"Skills: {payload['content'].get('skills_acquired', '')}\n\n"
        "Return ONLY the paragraph."
    )
