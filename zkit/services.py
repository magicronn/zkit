import pandas as pd
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker, joinedload
from .models import Plan, Pillar, CapacityPlan, ResourceCapacity, ProjectEstimate, Project, Delivery, db

def loadPillarCapacityPlans(plan_id):
    # Create a new session
    session = db.session()

    # Perform grouped query
    query = session.query(
        Plan.id.label('plan_id'),
        Pillar.id.label('pillar_id'),
        ResourceCapacity.planSlice,
        ResourceCapacity.resType.label('resource_type_id'),
        func.sum(ResourceCapacity.capacity).label('capacity'),
    ).join(Pillar, Plan.id == Pillar.plan
    ).join(CapacityPlan, Pillar.id == CapacityPlan.pillar
    ).join(ResourceCapacity, CapacityPlan.id == ResourceCapacity.capacityPlan
    ).filter(Plan.id == plan_id
    ).group_by(
        Plan.id,
        Pillar.id,
        ResourceCapacity.planSlice,
        ResourceCapacity.resType
    )

    # Convert query to SQL statement
    stmt = query.statement

    # Create a new engine
    engine = create_engine('sqlite:////tmp/test.db')

    # Execute the statement and fetch all results into a pandas DataFrame
    df = pd.read_sql(stmt, engine)

    return df

def extendPillarCapacities(df):
    # Sort dataframe by 'planSlice' in ascending order
    df = df.sort_values(by='planSlice')
    
    # Group by 'plan_id', 'project_id', 'pillar_id', then calculate running total of 'capacity' within each group
    df['running_capacity'] = df.groupby(['plan_id', 'project_id', 'pillar_id'])['capacity'].cumsum()
    
    return df

def loadProjectEstimates(plan_id):
    # establish a session
    session = db.session() 

    # Perform the query and convert to DataFrame
    query = session.query(
        Plan.id.label('plan_id'),
        Project.id.label('project_id'),
        Project.rank.label('project_rank'),
        Project.dueDate.label('due_date'),
        Pillar.id.label('pillar_id'),
        ProjectEstimate.resType.label('resType_id'),
        ProjectEstimate.estimate
    ).join(Project, Plan.id == Project.plan
    ).join(Pillar, Project.pillar == Pillar.id
    ).join(ProjectEstimate, Project.id == ProjectEstimate.project
    ).filter(Plan.id == plan_id)

    # Convert to DataFrame
    # TODO: Bug in VSCode?
    df = pd.read_sql(query.statement, con=session.bind)
    return df

def extendProjectEstimates(df):
    # Sort by project_rank
    df = df.sort_values(by='project_rank')

    # Create running_estimate column that is the cumulative sum by group
    df['running_estimate'] = df.groupby(['plan_id', 'project_id', 'pillar_id', 'resType_id'])['estimate'].cumsum()

    return df

def updateDeliveries(plan_id):
    # Create a new session
    session = db.session

    # Load pillar capacity plans
    dfCap = loadPillarCapacityPlans(plan_id)

    # Extend pillar capacities
    dfCap = extendPillarCapacities(dfCap)

    # Load project estimates
    dfEst = loadProjectEstimates(plan_id)

    # Extend project estimates
    dfEst = extendProjectEstimates(dfEst)

    # Extend the dfEst dataframe with a new column: 'delivery_slice'
    dfCap = dfCap.sort_values(by=['pillar_id', 'resource_type_id', 'planSlice', 'running_capacity'], ascending=True)
    dfEst['delivery_slice'] = pd.merge_asof(dfEst.sort_values('running_estimate'), 
                                            dfCap, 
                                            left_on='running_estimate', 
                                            right_on='running_capacity', 
                                            by=['pillar_id', 'resource_type_id'], 
                                            direction='forward')['planSlice']
    
    # Group by plan_id, project_id, pillar_id and take the max of delivery_slice
    dfEst = dfEst.groupby(['plan_id', 'project_id', 'pillar_id']).agg({'delivery_slice': 'max'}).reset_index()

    # Convert dfEst to a list of dictionaries
    dfEst_dict = dfEst.to_dict('records')

    for row in dfEst_dict:
        # Check if a delivery already exists for the plan and project
        delivery = session.query(Delivery).filter_by(plan=row['plan_id'], project=row['project_id']).first()

        if delivery:
            # Update the existing delivery
            delivery.deliverySlice = row['delivery_slice']
        else:
            # Insert a new delivery
            new_delivery = Delivery(plan=row['plan_id'],
                                    project=row['project_id'],
                                    deliverySlice=row['delivery_slice'],
                                    deliveredFlag=False,
                                    startDate=None,
                                    endDate=None)
            session.add(new_delivery)

    # Commit the session to save changes to the database
    session.commit()

    return dfEst






