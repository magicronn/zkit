import datetime
from flask import request, jsonify
from flask_restful import reqparse, inputs, Api, Resource
from sqlalchemy import func, and_
from .models import db, Plan, Project, Pillar, CapacityPlan, ResourceCapacity, ResourceType, Delivery, ProjectEstimate

api = Api()

# helper function to optimize verification of a list of ResourceCapacity objects
def get_resource_types_dict():
    resource_types = ResourceType.query.all()
    resource_types_dict = {rt.name: rt for rt in resource_types}
    return resource_types_dict


def verify_resource_capacity_types(resource_capacities, resource_types_dict):
    for rc in resource_capacities:
        if rc['resType'] not in resource_types_dict:
            return False
    return True


@api.resource('/plans')
class PlanListResource(Resource):
    def get(self):
        plans = Plan.query.all()
        response = []

        for plan in plans:
            response.append({
                'id': plan.id,
                'name': plan.name,
                'startDate': plan.startDate.isoformat(),
                'cntSliceMonth': plan.cntSliceMonth,
                'cntSliceWeek': plan.cntSliceWeek,
                'cntSliceDay': plan.cntSliceDay,
                'cntSlices': plan.cntSlices,
            })

        return response, 200


@api.resource('/plans/<int:id>')
class PlanResource(Resource):
    def get(self, id):
        plan = Plan.query.get(id)
        if plan is None:
            return {'message': f'No Plan found with ID: {id}'}, 404

        response = {
            'id': plan.id,
            'name': plan.name,
            'startDate': plan.startDate.isoformat(),
            'endDate' : plan.endDate.isoformat(),
            'cntSliceMonth': plan.cntSliceMonth,
            'cntSliceWeek': plan.cntSliceWeek,
            'cntSliceDay': plan.cntSliceDay,
            'cntSlices': plan.cntSlices,
        }

        return response, 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('startDate', type=str, required=True, help='startDate cannot be blank')
        parser.add_argument('endDate', type=str, required=True, help='endDate cannot be blank')
        parser.add_argument('cntSliceMonth', type=int, required=True, help='cntSliceMonth cannot be blank')
        parser.add_argument('cntSliceWeek', type=int, required=True, help='cntSliceWeek cannot be blank')
        parser.add_argument('cntSliceDay', type=int, required=True, help='cntSliceDay cannot be blank')
        parser.add_argument('cntSlices', type=int, required=True, help='cntSlices cannot be blank')
        args = parser.parse_args()

        new_plan = Plan(
            name=args['name'], 
            startDate=datetime.datetime.strptime(args['startDate'], '%Y-%m-%d'), 
            endDate = datetime.datetime.strptime(args['endDate'], '%Y-%m-%d'),
            cntSliceMonth=args['cntSliceMonth'],
            cntSliceWeek=args['cntSliceWeek'],
            cntSliceDay=args['cntSliceDay'],
            cntSlices=args['cntSlices'],
        )

        db.session.add(new_plan)
        db.session.commit()

        return {'message': 'Plan created successfully', 'id': new_plan.id}, 201

    def put(self, plan_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('startDate', type=str, required=True, help='startDate cannot be blank')
        parser.add_argument('endDate', type=str, required=True, help='endDate cannot be blank')
        parser.add_argument('cntSliceMonth', type=int, required=True, help='cntSliceMonth cannot be blank')
        parser.add_argument('cntSliceWeek', type=int, required=True, help='cntSliceWeek cannot be blank')
        parser.add_argument('cntSliceDay', type=int, required=True, help='cntSliceDay cannot be blank')
        parser.add_argument('cntSlices', type=int, required=True, help='cntSlices cannot be blank')
        args = parser.parse_args()

        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        plan.name = args['name']
        plan.startDate = datetime.datetime.strptime(args['startDate'], '%Y-%m-%d')
        plan.endDate = datetime.datetime.strptime(args['endDate'], '%Y-%m-%d')
        plan.cntSliceMonth = args['cntSliceMonth']
        plan.cntSliceWeek = args['cntSliceWeek']
        plan.cntSliceDay = args['cntSliceDay']
        plan.cntSlices = args['cntSlices']
        
        db.session.commit()

        return {'message': 'Plan updated successfully'}, 200

    def delete(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        db.session.delete(plan)
        db.session.commit()

        return {'message': 'Plan deleted successfully'}, 200

    
@api.resource('/plans/<int:plan_id>/summary')
class PlanSummaryResource(Resource):
    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        # calculate programSpendTotal
        program_spend_total = db.session.query(func.sum(Project.programSpend)).filter(Project.plan == plan_id).scalar()

        # calculate cntAllProjects
        cnt_all_projects = Project.query.filter(and_(Project.plan == plan_id, Project.parent.is_(None))).count()

        # calculate cntCrossPillarProjects
        cnt_cross_pillar_projects = db.session.query(Project.parent).filter(and_(Project.plan == plan_id, Project.parent.isnot(None))).distinct().count()

        # calculate cntCommittedProjects
        cnt_committed_projects = db.session.query(Project).join(Delivery, Project.id == Delivery.project).filter(and_(Project.plan == plan_id, Project.parent.is_(None), Delivery.endDate <= plan.endDate)).count()

        # calculate cntOverdueProjects
        cnt_overdue_projects = db.session.query(Project).join(Delivery, Project.id == Delivery.project).filter(and_(Project.plan == plan_id, Project.parent.is_(None), Delivery.endDate > Project.dueDate)).count()

        plan_summary = {
            'programSpendTotal': float(program_spend_total) if program_spend_total else 0,  # cast to float or return 0 if None
            'cntAllProjects': cnt_all_projects,
            'cntCrossPillarProjects': cnt_cross_pillar_projects,
            'cntCommittedProjects': cnt_committed_projects,
            'cntOverdueProjects': cnt_overdue_projects,
        }

        return plan_summary, 200


@api.resource('/pillars/<int:pillar_id>/capacity_plans')
class PillarCapacityPlansResource(Resource):
    def get(self, pillar_id):
        pillar = Pillar.query.get(pillar_id)

        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        capacity_plans = CapacityPlan.query.filter_by(pillar=pillar.id).all()

        if not capacity_plans:
            return {'message': f'No Capacity Plans found for Pillar ID: {pillar_id}'}, 404

        capacity_plans_list = []
        for cp in capacity_plans:
            # Fetch the associated ResourceCapacity objects
            resource_capacities = ResourceCapacity.query.filter_by(capacityPlan=cp.id).all()

            # Build a list of the associated ResourceCapacity objects for each CapacityPlan
            resource_capacities_list = []
            for rc in resource_capacities:
                # Fetch the associated ResourceType
                res_type = ResourceType.query.get(rc.resType)
                resource_capacities_list.append({
                    'id': rc.id,
                    'resType': res_type.name if res_type else "No resource type",
                    'planSlice': rc.planSlice,
                    'capacity': rc.capacity
                })

            # Append the CapacityPlan and its associated ResourceCapacities to the list
            capacity_plans_list.append({
                'id': cp.id,
                'name': cp.name,
                'pillar': cp.pillar,
                'resourceCapacities': resource_capacities_list
            })

        return jsonify(capacity_plans_list)
    
    def post(self, pillar_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('pillar', type=int, required=True, help='Pillar cannot be blank')
        parser.add_argument('resourceCapacities', type=list, location='json', required=True)

        args = parser.parse_args()

        pillar = Pillar.query.get(pillar_id)
        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        new_capacity_plan = CapacityPlan(name=args['name'], pillar=pillar_id)
        db.session.add(new_capacity_plan)
        db.session.flush()  # flush the session to generate new_capacity_plan.id

        res_types = get_resource_types_dict()
        if verify_resource_capacity_types(args['resourceCapacities'], res_types) is False:
            db.session.rollback()
            return {'message': f'No ResourceType found with name <TBD>'}, 404
            #TODO: Get name of ResourceType that failed verification

        resource_capacities_list = []
        for rc in args['resourceCapacities']:
            res_type = res_types[rc['resType']]
            new_resource_capacity = ResourceCapacity(capacityPlan=new_capacity_plan.id, resType=res_type.id, planSlice=rc['planSlice'], capacity=rc['capacity'])
            db.session.add(new_resource_capacity)
            
            # Add the new ResourceCapacity to the list
            resource_capacities_list.append({
                'id': new_resource_capacity.id,
                'resType': res_type.name,
                'planSlice': new_resource_capacity.planSlice,
                'capacity': new_resource_capacity.capacity
            })

        db.session.commit()

        # Build the response
        response = {
            'message': 'CapacityPlan created successfully',
            'capacityPlan': {
                'id': new_capacity_plan.id,
                'name': new_capacity_plan.name,
                'pillar': new_capacity_plan.pillar,
                'resourceCapacities': resource_capacities_list
            }
        }

        return response, 201

    def put(self, pillar_id, capacity_plan_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('resourceCapacities', type=list, location='json', required=True)

        args = parser.parse_args()

        pillar = Pillar.query.get(pillar_id)
        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        capacity_plan = CapacityPlan.query.get(capacity_plan_id)
        if capacity_plan is None or capacity_plan.pillar != pillar_id:
            return {'message': f'No CapacityPlan found with ID: {capacity_plan_id} for Plan ID: {pillar_id}'}, 404

        capacity_plan.name = args['name']
        capacity_plan.pillar = args['pillar']

        # Remove old ResourceCapacities
        ResourceCapacity.query.filter_by(capacityPlan=capacity_plan_id).delete()

        res_types = get_resource_types_dict()

        if verify_resource_capacity_types(args['resourceCapacities'], res_types) is False:
            db.session.rollback()
            return {'message': f'No ResourceType found with name <TODO: Get name>'}, 404
            #TODO: Get name of ResourceType that failed verification
        
        resource_capacities_list = []
        for rc in args['resourceCapacities']:
            res_type = res_types[rc['resType']]
            new_resource_capacity = ResourceCapacity(capacityPlan=capacity_plan_id, resType=res_type.id, planSlice=rc['planSlice'], capacity=rc['capacity'])
            db.session.add(new_resource_capacity)

             # Add the new ResourceCapacity to the list
            resource_capacities_list.append({
                'id': new_resource_capacity.id,
                'resType': res_type.name,
                'planSlice': new_resource_capacity.planSlice,
                'capacity': new_resource_capacity.capacity
            })

        db.session.commit()

        response = {
            'message': 'CapacityPlan updated successfully',
            'capacityPlan': {
                'id': capacity_plan.id,
                'name': capacity_plan.name,
                'pillar': capacity_plan.pillar,
                'resourceCapacities': resource_capacities_list
            }
        }

        return response, 200

    def delete(self, pillar_id, capacity_plan_id):
        pillar = Pillar.query.get(pillar_id)
        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        capacity_plan = CapacityPlan.query.get(capacity_plan_id)
        if capacity_plan is None or capacity_plan.pillar != pillar_id:
            return {'message': f'No CapacityPlan found with ID: {capacity_plan_id} for Plan ID: {pillar_id}'}, 404

        # First, delete the related ResourceCapacity objects
        ResourceCapacity.query.filter_by(capacityPlan=capacity_plan_id).delete()

        # Then, delete the CapacityPlan itself
        db.session.delete(capacity_plan)
        db.session.commit()

        return {'message': 'CapacityPlan deleted successfully'}, 200


@api.resource('/plans/<int:plan_id>/pillars')
class PlanPillarsResource(Resource):
    def get(self, plan_id):
        pillars = Pillar.query.filter_by(plan=plan_id).all()
        if not pillars:
            return {'message': f'No Pillars found for Plan with ID: {plan_id}'}, 404

        response = []

        for pillar in pillars:
            response.append({
                'id': pillar.id,
                'plan': pillar.plan,
                'name': pillar.name,
                'abbreviation': pillar.abbreviation,
                'basePlan': pillar.basePlan,
                'adjustmentPlan': pillar.adjustmentPlan,
            })

        return response, 200

    def post(self, plan_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('abbreviation', type=str, required=True, help='Abbreviation cannot be blank')
        parser.add_argument('basePlan', type=int, required=False)
        parser.add_argument('adjustmentPlan', type=int, required=False)
        args = parser.parse_args()

        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        if args['basePlan'] is None:
            basePlan = CapacityPlan(name=f"Base Plan for {args['name']}", pillar=plan_id)
            db.session.add(basePlan)
            db.session.flush()  # flush the session to generate basePlan.id
            args['basePlan'] = basePlan.id

        if args['adjustmentPlan'] is None:
            adjustmentPlan = CapacityPlan(name=f"Adjustment Plan for {args['name']}", pillar=plan_id)
            db.session.add(adjustmentPlan)
            db.session.flush()  # flush the session to generate adjustmentPlan.id
            args['adjustmentPlan'] = adjustmentPlan.id

        new_pillar = Pillar(
            plan=plan_id,
            name=args['name'],
            abbreviation=args['abbreviation'],
            basePlan=args['basePlan'],
            adjustmentPlan=args['adjustmentPlan']
        )

        db.session.add(new_pillar)
        db.session.commit()

        return {'message': 'Pillar created successfully', 'id': new_pillar.id}, 201

    def put(self, plan_id, pillar_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('abbreviation', type=str, required=True, help='Abbreviation cannot be blank')
        parser.add_argument('basePlan', type=int, required=False)
        parser.add_argument('adjustmentPlan', type=int, required=False)
        args = parser.parse_args()

        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        pillar = Pillar.query.get(pillar_id)
        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        if args['basePlan'] is None and pillar.basePlan is None:
            basePlan = CapacityPlan(name=f"Base Plan for {args['name']}", pillar=plan_id)
            db.session.add(basePlan)
            db.session.flush()  # flush the session to generate basePlan.id
            args['basePlan'] = basePlan.id

        if args['adjustmentPlan'] is None and pillar.adjustmentPlan is None:
            adjustmentPlan = CapacityPlan(name=f"Adjustment Plan for {args['name']}", pillar=plan_id)
            db.session.add(adjustmentPlan)
            db.session.flush()  # flush the session to generate adjustmentPlan.id
            args['adjustmentPlan'] = adjustmentPlan.id

        pillar.name = args['name']
        pillar.abbreviation = args['abbreviation']
        pillar.basePlan = args['basePlan'] or pillar.basePlan
        pillar.adjustmentPlan = args['adjustmentPlan'] or pillar.adjustmentPlan

        db.session.commit()

        return {'message': 'Pillar updated successfully'}, 200

    def delete(self, plan_id, pillar_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        pillar = Pillar.query.get(pillar_id)
        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        base_plan = CapacityPlan.query.get(pillar.basePlan)
        adjustment_plan = CapacityPlan.query.get(pillar.adjustmentPlan)
        
        if base_plan:
            db.session.delete(base_plan)

        if adjustment_plan:
            db.session.delete(adjustment_plan)

        db.session.delete(pillar)
        db.session.commit()

        return {'message': f'Pillar with ID {pillar_id} deleted'}, 200


@api.resource('/plans/<int:plan_id>/projects')
class PlanProjectsResource(Resource):
    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        projects = Project.query.filter_by(plan=plan_id).all()
        if not projects:
            return {'message': 'No Projects found for this Plan ID'}, 404

        project_dicts = []
        for project in projects:
            # Convert SQLAlchemy object to dictionary
            project_dict = project.to_dict()

            # Query sub-projects for this project
            sub_projects = Project.query.filter_by(parent=project.id).all()
            project_dict['children'] = [sub_project.to_dict() for sub_project in sub_projects]

            project_dicts.append(project_dict)

        return {'projects': project_dicts}, 200

    def post(self, plan_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
        parser.add_argument('description', type=str, required=True, help='Description cannot be blank')
        parser.add_argument('rank', type=int, required=True, help='Rank cannot be blank')
        parser.add_argument('state', type=str, required=True, help='State cannot be blank')
        parser.add_argument('docLink', type=str, required=False)
        parser.add_argument('parent', type=int, required=False)
        parser.add_argument('pillar', type=int, required=True, help='Pillar ID cannot be blank')
        args = parser.parse_args()

        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        pillar = Pillar.query.get(args['pillar'])
        if pillar is None:
            return {'message': f'No Pillar found with ID: {args["pillar"]}'}, 404

        new_project = Project(
            name=args['name'],
            description=args['description'],
            rank=args['rank'],
            state=args['state'],
            docLink=args['docLink'],
            parent=args['parent'],
            pillar=args['pillar'],
            plan=plan_id
        )

        db.session.add(new_project)
        db.session.commit()

        return {'message': 'Project created successfully', 'project': new_project.to_dict()}, 201

    def put(self, plan_id):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True, help='Project ID cannot be blank')
        parser.add_argument('name', type=str, required=False)
        parser.add_argument('description', type=str, required=False)
        parser.add_argument('rank', type=int, required=False)
        parser.add_argument('state', type=str, required=False)
        parser.add_argument('docLink', type=str, required=False)
        parser.add_argument('parent', type=int, required=False)
        parser.add_argument('pillar', type=int, required=False)
        args = parser.parse_args()

        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        project = Project.query.get(args['id'])
        if project is None:
            return {'message': f'No Project found with ID: {args["id"]}'}, 404

        if args['pillar']:
            pillar = Pillar.query.get(args['pillar'])
            if pillar is None:
                return {'message': f'No Pillar found with ID: {args["pillar"]}'}, 404
            else:
                project.pillar = args['pillar']

        for field in ['name', 'description', 'rank', 'state', 'docLink', 'parent']:
            if args[field] is not None:
                setattr(project, field, args[field])

        db.session.commit()

        return {'message': 'Project updated successfully', 'project': project.to_dict()}, 200
    
    def delete(self, plan_id):
        parser = reqparse.RequestParser()
        parser.add_argument('id', type=int, required=True, help='Project ID cannot be blank')
        args = parser.parse_args()

        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        project = Project.query.get(args['id'])
        if project is None:
            return {'message': f'No Project found with ID: {args["id"]}'}, 404

        db.session.delete(project)
        db.session.commit()

        return {'message': f'Project with ID: {args["id"]} deleted successfully'}, 200


@api.resource('/plans/<int:plan_id>/pillars/<int:pillar_id>/projects')
class PlanPillarProjectsResource(Resource):
    def get(self, plan_id, pillar_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        pillar = Pillar.query.get(pillar_id)
        if pillar is None:
            return {'message': f'No Pillar found with ID: {pillar_id}'}, 404

        projects = Project.query.filter_by(plan=plan_id, pillar_id=pillar_id).all()

        project_dicts = []
        for project in projects:
            # Convert SQLAlchemy object to dictionary
            project_dict = project.to_dict()

            # Query sub-projects for this project
            sub_projects = Project.query.filter_by(parent=project.id).all()
            project_dict['children'] = [sub_project.to_dict() for sub_project in sub_projects]

            project_dicts.append(project_dict)

        return {'projects': project_dicts}, 200


@api.resource('/projects/<int:project_id>/estimates')
class ProjectEstimateResources(Resource):
    def put(self, project_id):
        parser = reqparse.RequestParser()
        parser.add_argument('estimates', type=list, location='json', required=True)

        args = parser.parse_args()

        project = Project.query.get(project_id)
        if project is None:
            return {'message': f'No Project found with ID: {project_id}'}, 404

        # First delete existing ProjectEstimates
        ProjectEstimate.query.filter_by(project=project_id).delete()

        # Now add new ProjectEstimates
        for estimate_dict in args['estimates']:
            estimate = ProjectEstimate(project=project_id, 
                                       resType=estimate_dict['resType'], 
                                       estimate=estimate_dict['estimate'])
            db.session.add(estimate)

        db.session.commit()

        return {'message': f'ProjectEstimates updated successfully'}, 200

    def delete(self, project_id):
        project = Project.query.get(project_id)
        if project is None:
            return {'message': f'No Project found with ID: {project_id}'}, 404

        # Delete existing ProjectEstimates
        ProjectEstimate.query.filter_by(project=project_id).delete()

        db.session.commit()

        return {'message': f'ProjectEstimates deleted successfully'}, 200

        
@api.resource('/plans/<int:plan_id>/deliveries')
class PlanDeliveriesResource(Resource):
    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {'message': f'No Plan found with ID: {plan_id}'}, 404

        deliveries = Delivery.query.filter_by(plan=plan_id).all()
        deliveries_dict = {}

        for delivery in deliveries:
            # Convert SQLAlchemy object to dictionary
            delivery_dict = delivery.to_dict()

            # Fetch project for this delivery
            project = Project.query.get(delivery.project)

            if project.parent:
                # if this project is a sub-project, update the delivery of the parent project if this delivery's endDate is later
                if deliveries_dict.get(project.parent):
                    if deliveries_dict[project.parent]['endDate'] < delivery_dict['endDate']:
                        deliveries_dict[project.parent] = delivery_dict
                continue  # sub-projects are not directly included in the map, only the parents are
            
            # For projects that are not sub-projects, or parent projects where this is the first sub-project being processed
            if deliveries_dict.get(delivery.project) is None or deliveries_dict[delivery.project]['endDate'] < delivery_dict['endDate']:
                deliveries_dict[delivery.project] = delivery_dict

        return deliveries_dict, 200

