import random
from typing import Dict
import pytest
from datetime import datetime, timedelta
import json
from flask import jsonify
from zkit.models import Plan, Pillar, CapacityPlan, ResourceCapacity, ResourceType, Delivery, Project, ProjectEstimate, db
from zkit.services import updateDeliveries

json_file_pairs = [
    ("zbb_json_1.json", "deliveries_json_1.json"),
    ("zbb_json_2.json", "deliveries_json_2.json"),
    # Add more pairs as needed...
]


def create_zbb_from_json(app, data: Dict) -> Dict[str, int]:
    with app.app_context():
        # Start by creating a Plan
        plan = Plan(data['plan']['name'], datetime.strptime(data['plan']['startDate'], "%Y-%m-%d"),
                    datetime.strptime(data['plan']['endDate'], "%Y-%m-%d"), data['plan']['cntSlices'])
        db.session.add(plan)
        db.session.commit()

        res_type_ids = {}
        # Next, create ResourceTypes
        for res_type in data['plan']['resourceTypes']:
            res_type_obj = ResourceType.query.filter_by(name=res_type['name']).first()
            if res_type_obj is None:
                raise ValueError(f"ResourceType {res_type['name']} does not exist")
            res_type_ids[res_type['name']] = res_type_obj.id

        # Now, create Pillars, CapacityPlans, and ResourceCapacities
        pillar_ids = {}
        for pillar in data['plan']['pillars']:
            pillar_obj = Pillar(pillar['name'], pillar['abbreviation'], plan.id)
            db.session.add(pillar_obj)
            db.session.commit()
            pillar_ids[pillar['name']] = pillar_obj.id

            for cp in pillar['capacityPlans']:
                cp_obj = CapacityPlan(cp['name'], pillar_obj.id)
                db.session.add(cp_obj)
                db.session.commit()

                for rc in cp['resourceCapacities']:
                    if rc['resType'] not in res_type_ids:
                        raise ValueError(f"ResourceType {rc['resType']} does not exist")
                    rc_obj = ResourceCapacity(cp_obj.id, res_type_ids[rc['resType']], rc['planSlice'], rc['capacity'])
                    db.session.add(rc_obj)
                    db.session.commit()

        # Finally, create Projects and ProjectEstimates
        for project in data['plan']['projects']:
            if project['pillar'] not in pillar_ids:
                raise ValueError(f"Pillar {project['pillar']} does not exist")
            if project['plan'] != plan.name:
                raise ValueError(f"Plan {project['plan']} does not exist")
                
            project_obj = Project(project['name'], pillar_ids[project['pillar']], project['rank'], plan.id)
            db.session.add(project_obj)
            db.session.commit()

            for pe in project['projectEstimates']:
                if pe['resType'] not in res_type_ids:
                    raise ValueError(f"ResourceType {pe['resType']} does not exist")
                pe_obj = ProjectEstimate(project_obj.id, res_type_ids[pe['resType']], pe['estimate'])
                db.session.add(pe_obj)
                db.session.commit()

        return {'plan_id': plan.id}
    
def compare_deliveries_from_json(app, plan_id: int, data: Dict) -> bool:
    with app.app_context():
        # Query the Plan from DB
        plan = Plan.query.get(plan_id)
        if plan is None:
            raise ValueError(f"Plan with id {plan_id} does not exist")

        # For each Delivery in the JSON data
        for delivery in data['deliveries']:
            # Look up the Project by name
            project = Project.query.filter_by(name=delivery['project']).first()
            if project is None:
                raise ValueError(f"Project {delivery['project']} does not exist")

            # Look up the Delivery by the project id and deliverySlice
            db_delivery = Delivery.query.filter_by(project_id=project.id).first()
            if db_delivery is None:
                return False  # Delivery does not exist
            
            # Compare the deliverySlice if it is provided in the JSON
            if 'deliverySlice' in delivery:
                if db_delivery.deliverySlice != delivery['deliverySlice']:
                    return False  # Delivery slices do not match
            # Compare the startDate and endDate if they are provided in the JSON
            if 'startDate' in delivery:
                if db_delivery.startDate != datetime.strptime(delivery['startDate'], "%Y-%m-%d"):
                    return False  # Start dates do not match
            if 'endDate' in delivery:
                if db_delivery.endDate != datetime.strptime(delivery['endDate'], "%Y-%m-%d"):
                    return False  # End dates do not match

        # If we made it through all the deliveries without returning False, then they all match
        return True

@pytest.mark.parametrize("zbb_json_file, deliveries_json_file", json_file_pairs)
def test_update_deliveries(app, zbb_json_file, deliveries_json_file):
    with app.app_context():
        with open(zbb_json_file, 'r') as f:
            zbb_data = json.load(f)
        plan_id = create_zbb_from_json(app, zbb_data)['plan_id']
        
        updateDeliveries(plan_id)

        with open(deliveries_json_file, 'r') as f:
            deliveries_data = json.load(f)

        assert compare_deliveries_from_json(app, plan_id, deliveries_data)
