def stub_chapter_one(payload):
    company = payload["internship"]["company_name"]
    dept = payload["internship"]["department_at_company"]
    return {
        "intro": (
            "The Student Industrial Work Experience Scheme (SIWES) is a skill development programme "
            "designed to bridge the gap between academic theory and industrial practice for students of "
            "Nigerian tertiary institutions. This report documents the six-month placement undertaken at "
            f"{company} within the {dept}, and the technical and professional skills acquired in the course of "
            "that period."
        ),
        "background_itf": (
            "The Industrial Training Fund (ITF) is a Nigerian government agency established on 8 October 1971 "
            "through Decree No. 47 of 1971, now the Industrial Training Fund Act. It was created to promote and "
            "encourage the acquisition of industrial and commercial skills required for national economic "
            "development. Since its inception, the ITF has grown into one of the country's most important "
            "institutions for technical and vocational training."
        ),
        "core_objectives_itf": [
            "Provide, promote and encourage the acquisition of industrial and commercial skills required for national development.",
            "Train Nigerians to meet the manpower needs of the public and private sectors.",
            "Support the implementation of the Students Industrial Work Experience Scheme in tertiary institutions.",
            "Conduct research and consultancy services in areas related to industrial training.",
        ],
        "historical_background_siwes": (
            "The Students Industrial Work Experience Scheme was introduced in Nigeria in 1973 by the Industrial "
            "Training Fund. Its primary purpose was to bridge the gap between theoretical knowledge gained in "
            "academic institutions and the practical skills demanded by industry. The scheme was a response to "
            "the observation that graduates of Nigerian tertiary institutions often lacked the hands-on competence "
            "required to perform effectively in the workplace."
        ),
        "aim_of_siwes": (
            "The aim of SIWES is to expose students to industrial environments, enhance their practical skills, "
            "bridge the gap between theory and practice, and improve their employability after graduation."
        ),
        "objectives_of_siwes": [
            "Provision of practical experience to students",
            "Skill development",
            "Workplace preparedness",
            "Career guidance",
            "Strengthening academia-industry collaboration",
        ],
        "company_profile": (
            f"{company} operates within the Nigerian industrial sector and maintains modern process and control "
            f"infrastructure across its facilities. The {dept} is one of the technical departments of the company, "
            "responsible for the operation, maintenance and continuous improvement of the electrical, instrumentation "
            "and automation assets that keep production running reliably."
        ),
        "brief_history": (
            f"{company} has grown over the years into a recognised name within its sector, with operations supported by "
            "a workforce of engineers, technicians and skilled operators. The site at which this SIWES placement was "
            "carried out hosts a number of modern production lines that are highly instrumented and controlled by "
            "programmable logic controllers and distributed control systems."
        ),
        "organisational_structure_intro": (
            f"To manage operations efficiently, {company} adopts a hierarchical organisational structure that "
            "defines responsibilities clearly and ensures smooth coordination across departments. At the top of "
            "the hierarchy sits the Plant Director, who reports to the corporate office, and below the Plant "
            "Director sit several functional departments, each described briefly below."
        ),
        "departments": [
            {"name": "Production Department", "description": "Manages the core manufacturing process from raw material handling through to finished product, ensuring throughput targets and quality standards are met."},
            {"name": "Instrumentation and Automation Department", "description": "Responsible for the installation, calibration and maintenance of field instruments and control systems including PLCs, DCS and SCADA platforms."},
            {"name": "Mechanical Maintenance Department", "description": "Charged with the upkeep of mechanical and rotating equipment through scheduled preventive and corrective maintenance regimes."},
            {"name": "Electrical Maintenance Department", "description": "Maintains the medium- and low-voltage distribution network, transformers, motor control centres and standby generation."},
            {"name": "Health, Safety and Environment Department", "description": "Enforces compliance with safety regulations, environmental standards and occupational health requirements across the site."},
            {"name": "Quality Assurance / Quality Control Department", "description": "Operates the laboratory facilities and ensures that raw materials, in-process samples and finished products meet specification."},
            {"name": "Human Resources and Administration", "description": "Handles workforce recruitment, training, welfare, industrial relations and general administration."},
            {"name": "Finance and Accounts", "description": "Responsible for budgeting, cost control and financial reporting to ensure sustainable economic performance of the plant."},
        ],
    }


def stub_chapter_two(payload):
    tools = payload["content"].get("tools_used", [])
    return {
        "intro": (
            "This chapter presents the tools and equipment encountered during the placement, the modes of "
            "communication observed in the plant, and a thematic summary of the activities undertaken across "
            "the six-month period."
        ),
        "tools_intro": (
            "A wide range of tools, instruments and equipment was used during the placement. These are grouped "
            "below into hand tools, measuring and testing instruments, and specialised equipment."
        ),
        "hand_tools": [
            {"name": tools[i] if i < len(tools) else f"Hand Tool {i+1}",
             "description": "Used routinely for assembly, dismantling and minor repair work on field equipment and inside control panels. Handled with appropriate care and in line with the plant's safety procedures."}
            for i in range(min(4, len(tools)))
        ] or [{"name": "Multipurpose hand tools", "description": "A standard mechanic's hand tool set was issued at the start of the placement and used throughout for assembly and minor repair work."}],
        "measuring_instruments": [
            {"name": "Digital Multimeter", "description": "Used for measurement of voltage, current, resistance and continuity in control panels and field junction boxes during fault diagnosis and routine checks."},
            {"name": "Clamp Meter", "description": "Used to measure motor running currents without breaking the circuit, supporting condition monitoring of induction motors and verification of drive output."},
            {"name": "Insulation Resistance Tester", "description": "Used to confirm the integrity of motor windings and power cables by applying a high test voltage and reading the resistance to earth."},
        ],
        "specialised_equipment": [
            {"name": "Variable Frequency Drives", "description": "Drives used to control the speed and torque of induction motors driving conveyors and process equipment, configured through the manufacturer's software."},
            {"name": "Programmable Logic Controllers", "description": "Industrial digital controllers used to execute the control logic of process equipment, programmed in ladder logic via the manufacturer's engineering environment."},
            {"name": "Calibration Equipment", "description": "Pressure and temperature calibrators used to verify and adjust the response of field instruments against a reference standard."},
        ],
        "themes": [
            {"title": "SAFETY INDUCTION AND PLANT ORIENTATION",
             "paragraphs": [
                 "The placement began with a formal safety induction conducted by the Health, Safety and Environment department. The induction covered the plant's safety policy, hazard identification, the use of personal protective equipment, and the procedures for entering restricted areas of the site.",
                 "Following the safety induction, a guided tour of the site introduced the layout of the production lines, the location of utilities and the working environment of the department to which I was attached.",
             ]},
            {"title": "BASIC EQUIPMENT MAINTENANCE",
             "paragraphs": [
                 "Routine preventive maintenance activities were a constant feature of the placement. These included the cleaning of contactor terminals, tightening of cable terminations and replacement of worn auxiliary contacts on motor starter panels.",
                 "Maintenance activities were documented in the departmental log and discussed at the daily handover meeting between shifts.",
             ]},
            {"title": "INSTRUMENT CALIBRATION AND LOOP TESTING",
             "paragraphs": [
                 "I assisted in the calibration of pressure and temperature transmitters using bench calibrators and verified the corresponding 4–20 mA signal end-to-end from the field junction box into the control system marshalling cabinet.",
                 "Each calibration was recorded with as-found and as-left values, in line with the plant's instrument management procedures.",
             ]},
            {"title": "VARIABLE FREQUENCY DRIVE COMMISSIONING",
             "paragraphs": [
                 "I supported the commissioning of variable frequency drives on process equipment. This included parameter configuration, motor auto-tuning and verification of feedback signals from associated transmitters.",
                 "Particular attention was paid to acceleration and deceleration ramps to avoid nuisance tripping under heavy starting loads.",
             ]},
            {"title": "PLC PROGRAMMING AND TROUBLESHOOTING",
             "paragraphs": [
                 "Programmable logic controllers were programmed and debugged using the manufacturer's engineering environment. I built simple ladder logic programmes for interlocks and downloaded them to a training PLC in the workshop.",
                 "Where existing programmes required modification, changes were carried out under supervision, tested offline and only deployed during planned changeovers.",
             ]},
            {"title": "SCADA AND HMI CONFIGURATION",
             "paragraphs": [
                 "I worked with the SCADA team on the development of mimics for a new section of the plant. Tags were linked from the PLC, alarms were prioritised according to the plant's alarm philosophy and the screens were tested with the operations team.",
                 "I also helped configure a small HMI panel for a local control application and trained two operators on its basic navigation.",
             ]},
            {"title": "THERMOGRAPHIC AND CONDITION-BASED INSPECTIONS",
             "paragraphs": [
                 "Periodic thermographic inspections were carried out on motor control centres and busbar connections using an infrared camera. Hotspots were logged and addressed during the next planned outage.",
                 "These inspections gave me a practical understanding of the value of condition-based maintenance in reducing unplanned downtime.",
             ]},
            {"title": "DOCUMENTATION AND STANDARD OPERATING PROCEDURES",
             "paragraphs": [
                 "Towards the end of the placement, I contributed to the documentation of recurring maintenance tasks by drafting standard operating procedures for VFD parameter back-up and PLC project archival. The procedures were reviewed by the supervisor and added to the departmental document register.",
             ]},
        ],
    }


def stub_chapter_three(payload):
    challenges = payload["content"].get("challenges", [])
    problems_solved = payload["content"].get("problems_solved", [])
    table_rows = [{"problem": c.get("problem", ""), "solution": c.get("solution", "")} for c in challenges[:7]]
    if not problems_solved:
        problems_solved = [
            {"title": "Sensor Calibration", "narrative": "I assisted in the calibration of field sensors that were reporting drifted values to the control system, restoring confidence in the process measurements they provided."},
            {"title": "Drive Trip Investigation", "narrative": "I supported the investigation of a recurring drive trip by reviewing event logs and helping to identify a degraded feedback cable as the root cause."},
        ]
    return {
        "intro_3_1": (
            "Several challenges were encountered during the placement. These ranged from technical issues to "
            "practical limitations of access. Table 3.1 summarises the challenges and the solutions that were "
            "applied either by me or by the team I worked with."
        ),
        "table_rows": table_rows,
        "intro_3_2": (
            "Beyond the challenges listed in Table 3.1, the placement also presented opportunities to contribute "
            "to the solution of real engineering problems. The following narratives describe selected problems I "
            "helped to solve during the six-month period."
        ),
        "solved_items": [{"title": p.get("title", ""), "paragraph": p.get("narrative", "")} for p in problems_solved],
        "closing": (
            "Working through these problems developed my ability to apply theoretical knowledge in real-world "
            "scenarios, improved my troubleshooting methodology and showed me the value of teamwork in achieving "
            "timely solutions to industrial challenges."
        ),
    }


def stub_chapter_four(payload):
    skills = payload["content"].get("skills_acquired", "")
    return {
        "summary": (
            f"The six-month SIWES training at {payload['internship']['company_name']} during the period "
            f"{payload['internship']['duration']} provided first-hand exposure to industrial practice in the "
            f"{payload['internship']['department_at_company']}. The placement began with safety induction and "
            "plant orientation and progressed into hands-on participation in preventive and corrective "
            "maintenance, calibration, commissioning and troubleshooting activities."
        ),
        "conclusion": (
            "The SIWES programme was highly beneficial in bridging the gap between theoretical classroom "
            "knowledge and industrial practice. The exposure to real-time process automation strengthened my "
            "appreciation of mechatronics engineering and clarified the role of control systems in driving "
            "production efficiency. Overall, the experience has significantly improved my technical competence, "
            "professional confidence and readiness for engineering practice."
        ),
        "recommendations": [
            "Institutions should update their laboratories with modern process control equipment to align with industry standards.",
            "More opportunities should be given to students to interact with automation software during SIWES.",
            "Organisations should continue to support SIWES placements with structured work plans for interns.",
            "Students should engage in pre-SIWES self-study on industrial safety and core engineering software.",
        ],
    }


def stub_acknowledgement(payload):
    student = payload["student"]["name"]
    industry = payload["internship"].get("industry_supervisor_name", "the industry supervisor")
    academic = payload["internship"].get("academic_supervisor_name", "the academic supervisor")
    department = payload["student"]["department"]
    return (
        "I am grateful to God Almighty for the success of my SIWES programme and for sustaining me through every "
        f"stage of the training. My sincere appreciation goes to my industry-based supervisor, {industry}, for "
        "taking the time to instruct, correct and supervise me throughout the placement.\n\n"
        f"I extend my warm gratitude to my academic supervisor, {academic}, for his thoughtful guidance and steady "
        f"support, and to the kind lecturers of the Department of {department} for their teaching, advice and "
        "encouragement.\n\n"
        f"Finally, I appreciate my family and friends whose support made the entire experience possible. "
        f"Signed, {student}."
    )


def stub_abstract(payload):
    company = payload["internship"]["company_name"]
    dept = payload["internship"]["department_at_company"]
    duration = payload["internship"]["duration"]
    return (
        "The Students Industrial Work Experience Scheme (SIWES) is aimed at bridging the gap between academic "
        f"theory and industrial practice. This report presents the six-month training undertaken at {company} "
        f"during the period {duration} within the {dept}. The programme exposed the author to modern process "
        "automation, including the use of field instruments, programmable logic controllers, variable frequency "
        "drives and supervisory control systems, alongside calibration and maintenance procedures. The training "
        "also covered safety culture, documentation practices and teamwork in an industrial setting. Overall, "
        "the placement successfully bridged classroom theory with practical engineering work and strengthened "
        "the author's readiness for professional engineering practice."
    )
