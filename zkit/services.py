from typing import List, Dict, Union
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker, joinedload
from .models import Plan, Pillar, CapacityPlan, ResourceCapacity, ResourceType, ProjectEstimate, Project, Delivery, db

def loadPillarCapacityPlans(plan_id: int) -> List[Dict[str, Union[int, float, str]]]:
    # Query the database for all CapacityPlans and associated ResourceCapacities and ResourceTypes
    # associated with the given plan_id
    pillar_capacity_plans = (
        db.session.query(CapacityPlan, ResourceCapacity, ResourceType)
        .join(ResourceCapacity, CapacityPlan.id == ResourceCapacity.capacityPlan)
        .join(ResourceType, ResourceCapacity.resType == ResourceType.id)
        .filter(CapacityPlan.pillar == plan_id)
        .all()
    )

    # Convert the SQLAlchemy objects to dictionaries
    pillar_capacity_plan_dicts = [
        {
            'pillar_id': plan.pillar,
            'resource_type_id': res_type.id,
            'planSlice': resource_capacity.planSlice,
            'running_capacity': resource_capacity.capacity,
        } 
        for plan, resource_capacity, res_type in pillar_capacity_plans
    ]

    return pillar_capacity_plan_dicts

def loadProjectEstimates(plan_id: int) -> List[Dict[str, Union[int, float, str]]]:
    # Query the database for all Projects and associated ProjectEstimates
    # associated with the given plan_id
    project_estimates = (
        db.session.query(Project, ProjectEstimate, ResourceType)
        .join(ProjectEstimate, Project.id == ProjectEstimate.project)
        .join(ResourceType, ProjectEstimate.resType == ResourceType.id)
        .filter(Project.plan == plan_id)
        .all()
    )

    # Convert the SQLAlchemy objects to dictionaries
    project_estimate_dicts = [
        {
            'plan_id': project.plan,
            'project_id': project.id,
            'pillar_id': project.pillar,
            'rank': project.rank,
            'resource_type_id': res_type.id,
            'estimate': project_estimate.estimate,
        }
        for project, project_estimate, res_type in project_estimates
    ]

    return project_estimate_dicts

def updateDeliveries(plan_id):
    # Create a new session
    session = db.session

    # Load pillar capacity plans
    capacity_plans = loadPillarCapacityPlans(plan_id)

    # Load project estimates
    project_estimates = loadProjectEstimates(plan_id)

    # Sort capacity_plans and project_estimates
    capacity_plans.sort(key=lambda x: (x['pillar_id'], x['resource_type_id'], x['planSlice'], x['running_capacity'])) 
    project_estimates.sort(key=lambda x: x['rank']) 

    # Create a dictionary to track remaining capacities
    remaining_capacities = {plan['planSlice']: plan['running_capacity'] for plan in capacity_plans} 
    
    # Iterate over projects
    for project in project_estimates:
        running_estimate = 0
        delivery_slice = None

        # Iterate over plan slices
        for plan_slice, capacity in remaining_capacities.items():
            running_estimate += project['estimate'] # type: ignore
            
            # Check if the running estimate can be fulfilled
            if running_estimate <= capacity:
                delivery_slice = plan_slice
                remaining_capacities[plan_slice] -= running_estimate
                break
            else:
                running_estimate -= capacity
                remaining_capacities[plan_slice] = 0

        # Set delivery slice of the project
        # project['delivery_slice'] = delivery_slice

        # Check if a delivery already exists for the plan and project
        delivery = session.query(Delivery).filter_by(plan=plan_id, project=project['project_id']).first()

        if delivery:
            # Update the existing delivery
            delivery.deliverySlice = delivery_slice
        else:
            # Insert a new delivery
            new_delivery = Delivery(plan=plan_id,
                                    project=project['project_id'],
                                    deliverySlice=delivery_slice,
                                    deliveredFlag=False,
                                    startDate=None,
                                    endDate=None)
            session.add(new_delivery)

    # Commit the session to save changes to the database
    session.commit()

    return project_estimates







