from django.http import JsonResponse
from backend.firebase_config import db
from collections import defaultdict
from difflib import get_close_matches

def analytics_summary(request):
    try:
        # === Basic Totals ===
        total_users = len(list(db.collection("users").stream()))
        total_outlets = len(list(db.collection("outlets").stream()))
        total_rewards = len(list(db.collection("rewards").stream()))
        total_quests = len(list(db.collection("quests").stream()))

        # Helper: Normalize material names
        def clean_name(name):
            if not name:
                return ""
            name = name.strip().lower()
            if "made of" in name:
                name = name.split("made of")[0].strip()
            return name.title()

        # === Aggregation containers ===
        target_totals = defaultdict(int)
        collected_totals = defaultdict(int)

        def add_material(totals_dict, name, qty):
            name = clean_name(name)
            existing_names = totals_dict.keys()
            match = get_close_matches(name, existing_names, n=1, cutoff=0.85)
            if match:
                totals_dict[match[0]] += qty
            else:
                totals_dict[name] += qty

        # === STEP 1: Gather all submissions ===
        submissions = list(db.collection("submissions").stream())
        for submission in submissions:
            sdata = submission.to_dict()
            materials = sdata.get("materials", [])
            if isinstance(materials, list):
                for material in materials:
                    if isinstance(material, dict):
                        add_material(collected_totals, material.get("name"), material.get("quantity", 0))

        # === STEP 2: Compute Target Recyclables (sum across all quests) ===
        quests = db.collection("quests").stream()
        for quest in quests:
            qdata = quest.to_dict()
            materials = qdata.get("materials", [])
            if isinstance(materials, list):
                for material in materials:
                    if isinstance(material, dict):
                        qty = material.get("quantity")
                        # Default to 1 if missing or 0
                        if not qty or qty <= 0:
                            qty = 1
                        add_material(target_totals, material.get("name"), qty)

        # === STEP 3: Combine and progress computation ===
        target_total = sum(target_totals.values()) or 1
        collected_total = sum(collected_totals.values())
        all_materials = set(target_totals.keys()) | set(collected_totals.keys())

        materials_progress = []
        for name in all_materials:
            target_qty = target_totals.get(name, 0)
            collected_qty = collected_totals.get(name, 0)
            progress_percent = round((collected_qty / target_qty) * 100) if target_qty > 0 else 0
            capped_percent = min(progress_percent, 100)
            overachievement = max(progress_percent - 100, 0)
            materials_progress.append({
                "name": name,
                "target": target_qty,
                "collected": collected_qty,
                "progress_percent": capped_percent,
                "progress_display": f"{capped_percent}%" if overachievement == 0 else f"{progress_percent}% (over)",
                "overachievement_percent": overachievement
            })

        # === Sort Top 5 lists separately ===
        top_target_materials = sorted(
            materials_progress, key=lambda x: x["target"], reverse=True
        )[:5]

        top_collected_materials = sorted(
            materials_progress, key=lambda x: x["collected"], reverse=True
        )[:5]

        # === Overall Progress ===
        overall_percent = round((collected_total / target_total) * 100)
        capped_overall_percent = min(overall_percent, 100)
        overall = {
            "target_total": target_total,
            "collected_total": collected_total,
            "progress_percent": capped_overall_percent,
            "progress_display": f"{capped_overall_percent}%" if overall_percent <= 100 else f"{overall_percent}% (over)",
            "overachievement_percent": max(overall_percent - 100, 0)
        }

        # === Final Response ===
        return JsonResponse({
            "status": "success",
            "data": {
                "totals": {
                    "total_users": total_users,
                    "total_outlets": total_outlets,
                    "total_rewards": total_rewards,
                    "total_quests": total_quests,
                },
                "recyclables": {
                    "top_target_materials": top_target_materials,
                    "top_collected_materials": top_collected_materials,
                    "overall": overall
                }
            }
        }, safe=False)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
