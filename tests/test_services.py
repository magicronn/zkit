import random
import pytest
from datetime import datetime, timedelta
import json
from flask import jsonify
from zkit.models import Plan, Pillar, CapacityPlan, ResourceCapacity, ResourceType, Delivery, Project, ProjectEstimate, db
from zkit.services import updateDeliveries

def create_baseline_zbb(planSlices=1, num_pillars=1, num_capacity_plans=1, num_resource_types=1, num_projects=1, num_project_estimates=1):

    # Create a plan
    plan = Plan(name='Test Plan', startDate=datetime.now(), endDate=datetime.now() + timedelta(days=365), cntSlices=planSlices)
    db.session.add(plan)
    db.session.commit()

    # Create a pillar
    for idx in range(num_pillars):
        pillar = Pillar(name=f'Test Pillar {idx}', abbreviation=f'TP{idx}', plan=plan.id)
        db.session.add(pillar)
        db.session.commit()
    pillars = ResourceType.query.all()

    # Create a resource type
    for idx in range(num_resource_types):
        res_type = ResourceType(name=f'Test Resource Type {idx}', abbreviation=f'TRT{idx}')
        db.session.add(res_type)
        db.session.commit()
    res_types = ResourceType.query.all()

    # Create a capacity plan
    for idx in range(num_capacity_plans):
        #select a random pillar
        pillar = pillars[idx % num_pillars]
        capacity_plan = CapacityPlan(name=f'Test Capacity Plan {idx}', pillar=pillar.id)
        db.session.add(capacity_plan)
        db.session.commit()
    capacity_plans = CapacityPlan.query.all()

    for cp in capacity_plans:
        # select a random resource type
        res_type = res_types[cp.id % num_resource_types]
        for i in range(planSlices):
            resource_capacity = ResourceCapacity(capacity_plan=capacityPlan=cp.id, resType=res_type.id, planSlice=i, capacity=1)
            db.session.add(resource_capacity)
    db.session.commit()

    for idx in range(num_projects):
        # select a random pillar
        pillar = pillars[idx % num_pillars]
        project = Project(name=f'Test Project {idx}', pillar=pillar.id, plan=plan.id, rank=idx)
        db.session.add(project)
    db.session.commit()
    projects = Project.query.all()

    for project in projects:
        # select a random resource type
        res_type = res_types[project.id % num_resource_types]
        # create a random number of project_estimates less than planSlices
        estimate = random.randint(1, planSlices)
        for i in range(estimate):
            project_estimate = ProjectEstimate(project=project.id, resType=res_type.id, estimate=1)
            db.session.add(project_estimate)
    db.session.commit()

    return {
        'plan_id': plan.id,
        'pillars': pillars,
        'capacity_plans': capacity_plans,
        'resource_types': res_types,
        'projects': projects
    }

def test_update_deliveries(app):
    with app.app_context():
        with app.test_client() as client:
            
            zbb = create_baseline_zbb(planSlices=12, num_pillars=1, num_capacity_plans=1, num_resource_types=1, num_projects=1, num_project_estimates=1)

            # Call updateDeliveries function
            deliveries_updated = updateDeliveries(zbb['plan_id'])

            # Get all deliveries from the database
            all_deliveries = Delivery.query.all()

            # Assert that the number of deliveries equals the number of projects
            assert len(all_deliveries) == len(zbb['projects'])

            # Check each delivery's deliverySlice is not None
            for delivery in all_deliveries:
                assert delivery.deliverySlice is not None

            # Check that the result from updateDeliveries matches the state of the database
            for updated_delivery in deliveries_updated:
                delivery = Delivery.query.filter_by(plan=updated_delivery['plan_id'], project=updated_delivery['project_id']).first()
                assert delivery is not None
                assert delivery.deliverySlice == updated_delivery['delivery_slice']


            # Assert: Check the response data
            #assert response.status_code == 200
            #assert response.get_json()['name'] == 'Test Plan'
