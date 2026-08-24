"""Seed Landmark University as the first school. Idempotent — re-running is safe."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from api import auth as auth_mod
from api import schools as schools_repo
from api.db import init_db


LMU_DEGREES = [
    {"label": "B.Eng. Mechatronics Engineering", "short": "B.Eng."},
    {"label": "B.Eng. Mechanical Engineering", "short": "B.Eng."},
    {"label": "B.Eng. Electrical and Electronics Engineering", "short": "B.Eng."},
    {"label": "B.Eng. Civil Engineering", "short": "B.Eng."},
    {"label": "B.Sc. Computer Science", "short": "B.Sc."},
]
LMU_DEPARTMENTS = [
    "Mechanical and Mechatronics Engineering",
    "Electrical and Information Engineering",
    "Civil Engineering",
    "Agricultural Engineering",
    "Computer Science",
    "Mathematics and Statistics",
]
LMU_COLLEGES = [
    "College of Engineering",
    "College of Pure and Applied Sciences",
    "College of Agricultural Sciences",
]


def main():
    init_db()

    existing = schools_repo.get_school_by_slug("lmu")
    if existing:
        print(f"School 'lmu' already exists (id={existing['id']}). Skipping create.")
        school_id = existing["id"]
    else:
        school_id = schools_repo.create_school(
            slug="lmu",
            name="Landmark University",
            full_name="Landmark University, Omu-Aran",
            referral_prefix="LMU",
            logo_path="backend/assets/lmu_logo.png",
            platform_cut_pct=int(os.environ.get("PLATFORM_CUT_PCT", "20")),
        )
        print(f"Created Landmark University (id={school_id}).")

    schools_repo.update_school_config_bulk(school_id, {
        "degrees": json.dumps(LMU_DEGREES),
        "departments": json.dumps(LMU_DEPARTMENTS),
        "colleges": json.dumps(LMU_COLLEGES),
        "submission_clause": "SUBMITTED TO THE {department}, {college}, {university_full_name}",
        "award_clause": "IN PARTIAL FULFILMENT OF THE REQUIREMENT FOR AWARD OF BACHELOR OF ENGINEERING ({degree_short}) DEGREE IN MECHATRONICS ENGINEERING",
    })

    admins = schools_repo.list_school_admins(school_id)
    if not admins:
        username = "lmu_admin"
        pin = os.environ.get("LMU_ADMIN_INITIAL_PIN", "1234")
        schools_repo.create_school_admin(school_id, username, auth_mod.hash_pin(pin), "LMU Admin")
        print(f"Created school admin '{username}' with PIN '{pin}' (change immediately).")
    else:
        print(f"School admins already exist ({len(admins)}). Skipping.")

    print("Done.")


if __name__ == "__main__":
    main()
