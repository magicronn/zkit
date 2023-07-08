import pytest
from datetime import datetime, timedelta
import json
from flask import jsonify
from zkit.models import Plan, Pillar, CapacityPlan, ResourceCapacity, ResourceType, Delivery, Project, ProjectEstimate, db

def create_plan(name='Test Plan', startDate=None, endDate=None, cntSliceMonth=1, cntSliceWeek=0, cntSliceDay=0, cntSlices=12):
    if startDate is None:
        startDate = datetime.now()
    if endDate is None:
        endDate = datetime.now()

    plan = Plan(
        name=name, 
        startDate=startDate, 
        endDate=endDate,
        cntSliceMonth=cntSliceMonth,
        cntSliceWeek=cntSliceWeek,
        cntSliceDay=cntSliceDay,
        cntSlices=cntSlices,
    )
    return plan

def create_pillar(plan_id, name='Test Pillar', abbreviation='TP'):
    pillar = Pillar(
                plan=plan_id, 
                name=name, 
                abbreviation=abbreviation
            )
    return pillar

def create_baseline_zbb():
    # Create a plan
    plan = create_plan()
    db.session.add(plan)
    db.session.commit()

    # Create a pillar
    pillar = create_pillar(plan.id)
    db.session.add(pillar)
    db.session.commit()

    # Create a capacity plan
    capacity_plan = CapacityPlan(
        name='Test Capacity Plan',
        pillar=pillar.id,
    )
    db.session.add(capacity_plan)
    db.session.commit()

    # Create a resource type
    res_type = ResourceType(
        name='Test Resource Type',
        abbreviation='TRT',
    )
    db.session.add(res_type)
    db.session.commit()

    # Create a resource capacity
    for i in range(12):
        resource_capacity = ResourceCapacity(
            capacityPlan=capacity_plan.id,
            resType=res_type.id,
            planSlice=i,
            capacity=i
        )
        db.session.add(resource_capacity)
    db.session.commit()

    return {
        'plan_id': plan.id,
        'pillar_id': pillar.id,
        'capacity_plan_id': capacity_plan.id,
        'resource_type_id': res_type.id
    }

def test_get_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Your test code here
            # Arrange: Add a plan to the database
            plan = create_plan('Test Plan', startDate=datetime.now(), endDate=datetime.now())
            db.session.add(plan)
            db.session.commit()

            # Act: Send a GET request to /plans/<id>
            response = client.get(f'/plans/{plan.id}')

            # Assert: Check the response data
            assert response.status_code == 200
            assert response.get_json()['name'] == 'Test Plan'

def test_post_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Create a plan to send in the request
            plan = {
                'name': 'Test Plan',
                'startDate': datetime.now().date().isoformat(),
                'endDate': (datetime.now() + timedelta(days=10)).date().isoformat(),
                'cntSlices': 12
            }

            # Act: Send a POST request to /plans with the plan in the body
            response = client.post('/plans', json=plan)

            # Assert: Check the response data
            assert response.status_code == 201

def test_update_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Add a plan to the database
            plan = create_plan('Test Plan', startDate=datetime.now(), endDate=datetime.now())
            db.session.add(plan)
            db.session.commit()

            # Act: Send a PUT request to /plans/<id> to update the plan
            new_end_date = (datetime.now() + timedelta(days=10)).date().isoformat()
            response = client.put(
                f'/plans/{plan.id}',
                json={
                    'name': 'Updated Plan',
                    'startDate': plan.startDate.isoformat(),
                    'endDate': new_end_date,
                }
            )

            # Assert: Check the response data
            assert response.status_code == 200
            updated_plan = Plan.query.get(plan.id)
            assert updated_plan.name == 'Updated Plan'
            assert updated_plan.endDate.isoformat() == new_end_date

def test_delete_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Add a plan to the database
            plan = create_plan('Test Plan', startDate=datetime.now(), endDate=datetime.now())
            db.session.add(plan)
            db.session.commit()

            # Act: Send a DELETE request to /plans/<id>
            response = client.delete(f'/plans/{plan.id}')

            # Assert: Check the response status code and message
            assert response.status_code == 200
            assert response.get_json()['message'] == 'Plan deleted successfully'

            # Assert: Verify the plan is deleted
            assert Plan.query.get(plan.id) is None

def test_get_all_plans(app):
    # Use the app's context
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Add 10 plans to the database
            for i in range(10):
                plan = create_plan(f'Test Plan {i}', 
                                   startDate=datetime.now(), 
                                   endDate=datetime.now() + timedelta(days=i))
                db.session.add(plan)
            db.session.commit()

            # Act: Send a GET request to /plans
            response = client.get('/plans')

            # Assert: Check the response data
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 10  # There should be 10 plans
            for i in range(10):
                assert data[i]['name'] == f'Test Plan {i}'  # Plan names should match what was created
                assert 'startDate' in data[i]  # startDate should be in the response
                assert 'cntSliceMonth' in data[i]  # cntSliceMonth should be in the response
                assert 'cntSliceWeek' in data[i]  # cntSliceWeek should be in the response
                assert 'cntSliceDay' in data[i]  # cntSliceDay should be in the response
                assert 'cntSlices' in data[i]  # cntSlices should be in the response

def test_get_pillar_with_capacity_plans(app):
    with app.app_context():
        with app.test_client() as client:
            # Create baseline data
            id_dict = create_baseline_zbb()
            plan_id = id_dict["plan_id"]
            pillar_id = id_dict["pillar_id"]
            capacity_plan_id = id_dict["capacity_plan_id"]
            resource_type_id = id_dict["resource_type_id"]

            # Execute a GET request without including 'capacityPlans'
            response = client.get(f'/plans/{plan_id}/pillars/{pillar_id}')
            
            # Assert the status code and pillar details
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['id'] == pillar_id
            assert data['plan'] == plan_id
            assert 'capacityPlans' not in data

            # Execute a GET request including 'capacityPlans'
            response = client.get(f'/plans/{plan_id}/pillars/{pillar_id}?include=capacityPlans')
            
            # Assert the status code and pillar details
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['id'] == pillar_id
            assert data['plan'] == plan_id
            assert 'capacityPlans' in data
            assert isinstance(data['capacityPlans'], dict)
            assert len(data['capacityPlans']) > 0
            assert 'Test Capacity Plan' in data['capacityPlans']
            assert data['capacityPlans']['Test Capacity Plan']['id'] == capacity_plan_id
            assert data['capacityPlans']['Test Capacity Plan']['pillar'] == pillar_id

def test_post_pillar(app):
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Create a plan
            plan = create_plan('Test Plan', startDate=datetime.now(), endDate=datetime.now())
            db.session.add(plan)
            db.session.commit()

            # Act: Send a POST request to /plans/<plan_id>/pillars with a new pillar
            response = client.post(f'/plans/{plan.id}/pillars', json={
                'name': 'Test Pillar',
                'abbreviation': 'TP',
            })

            # Assert: Check the response data
            assert response.status_code == 201

def test_update_pillar(app):
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Create a plan and a pillar
            plan = create_plan('Test Plan', startDate=datetime.now(), endDate=datetime.now())
            db.session.add(plan)
            db.session.commit()

            pillar = Pillar(plan=plan.id, name='Test Pillar', abbreviation='TP')
            db.session.add(pillar)
            db.session.commit()

            # Act: Send a PUT request to /plans/<plan_id>/pillars/<pillar_id> with updated pillar data
            response = client.put(f'/plans/{plan.id}/pillars/{pillar.id}', json={
                'name': 'Updated Pillar',
                'abbreviation': 'UP',
            })

            # Assert: Check the response data
            assert response.status_code == 200
            data = response.get_json()
            assert data['message'] == 'Pillar updated successfully'

            # Further assertions can be made here to check if the Pillar was correctly updated in the database
            updated_pillar = Pillar.query.get(pillar.id)
            assert updated_pillar.name == 'Updated Pillar'
            assert updated_pillar.abbreviation == 'UP'

def test_delete_pillar(app):
    with app.app_context():
        with app.test_client() as client:
            # Arrange: Create a plan, a pillar and related capacity plans
            plan = create_plan('Test Plan', startDate=datetime.now(), endDate=datetime.now())
            db.session.add(plan)
            db.session.commit()

            pillar = Pillar(plan=plan.id, name='Test Pillar', abbreviation='TP')
            db.session.add(pillar)
            db.session.flush()

            base_plan = CapacityPlan(name='Base Plan for TP', pillar=pillar.id)
            adjustment_plan = CapacityPlan(name='Adjustment Plan for TP', pillar=pillar.id)

            db.session.add(base_plan)
            db.session.add(adjustment_plan)
            db.session.commit()

            # Act: Send a DELETE request to /plans/<plan_id>/pillars/<pillar_id>
            response = client.delete(f'/plans/{plan.id}/pillars/{pillar.id}')

            # Assert: Check the response data
            assert response.status_code == 200
            data = response.get_json()
            assert data['message'] == f'Pillar with ID {pillar.id} deleted'

            # Further assertions can be made here to check if the Pillar and related CapacityPlans were correctly deleted from the database
            deleted_pillar = Pillar.query.get(pillar.id)
            assert deleted_pillar is None

            deleted_base_plan = CapacityPlan.query.get(base_plan.id)
            assert deleted_base_plan is None

            deleted_adjustment_plan = CapacityPlan.query.get(adjustment_plan.id)
            assert deleted_adjustment_plan is None

def test_get_specific_capacity_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Create a plan and a pillar
            plan = create_plan()
            db.session.add(plan)
            db.session.commit()

            pillar = create_pillar(plan.id)
            db.session.add(pillar)
            db.session.commit()

            # Add capacity plans to the pillar
            cap_plan = CapacityPlan(name='Base Plan for TP', pillar=pillar.id)
            db.session.add(cap_plan)
            db.session.commit()

            # Execute a GET request
            response = client.get(f'/pillars/{pillar.id}/capacity_plans/{cap_plan.id}')

            # Check the status code is 200
            assert response.status_code == 200

            # Get the returned data
            data = response.get_json()

            # Check that the returned data is correct
            assert data['id'] == cap_plan.id
            assert data['name'] == 'Base Plan for TP'
            assert data['pillar'] == pillar.id

            # Check that the returned data has a key 'resourceCapacities' 
            assert 'resourceCapacities' in data

            # Check that 'resourceCapacities' is a list
            assert isinstance(data['resourceCapacities'], list)

            # As the test doesn't add any ResourceCapacity to the CapacityPlan, 
            # 'resourceCapacities' should be empty
            assert len(data['resourceCapacities']) == 0

def test_post_pillar_capacity_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Create a plan and a pillar
            plan = create_plan()
            db.session.add(plan)
            db.session.commit()

            pillar = create_pillar(plan.id)
            db.session.add(pillar)
            db.session.commit()

            # Prepare data for the new capacity plan
            new_capacity_plan_data = {
                'name': 'New Capacity Plan',
                'pillar': pillar.id
            }

            # Execute a POST request
            response = client.post(f'/pillars/{pillar.id}/capacity_plans', 
                                   data=json.dumps(new_capacity_plan_data), 
                                   content_type='application/json')

            # Check the status code is 201
            assert response.status_code == 201

            # Get the returned data
            data = response.get_json()

            # Check that the returned data is correct
            assert data['message'] == 'CapacityPlan created successfully'
            assert data['capacityPlan']['name'] == 'New Capacity Plan'
            assert data['capacityPlan']['pillar'] == pillar.id

            # Check that the returned data has a key 'resourceCapacities'
            assert 'resourceCapacities' in data['capacityPlan']

            # Check that 'resourceCapacities' is a list
            assert isinstance(data['capacityPlan']['resourceCapacities'], list)

            # Check the length of 'resourceCapacities'
            assert len(data['capacityPlan']['resourceCapacities']) == 0

def test_update_pillar_capacity_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Call the helper function to create the baseline ZBB.
            baseline_zbb_ids = create_baseline_zbb()

            # Use the returned IDs directly
            pillar_id = baseline_zbb_ids['pillar_id']
            capacity_plan_id = baseline_zbb_ids['capacity_plan_id']

            # Update data for the PUT request
            updated_capacity_plan_data = {
                'name': 'Updated Test Capacity Plan',
                'pillar': pillar_id,
                'resourceCapacities': [
                    {'resType': 'Test Resource Type', 'planSlice': i, 'capacity': 150} for i in range(12)
                ]
            }

            # Execute a PUT request
            response = client.put(f'/pillars/{pillar_id}/capacity_plans/{capacity_plan_id}', 
                                  data=json.dumps(updated_capacity_plan_data), 
                                  content_type='application/json')

            # Check status code
            assert response.status_code == 200

            # Check the response
            data = json.loads(response.data.decode())
            assert data['capacityPlan']['name'] == 'Updated Test Capacity Plan'
            assert data['capacityPlan']['pillar'] == pillar_id
            assert all(res_capacity['capacity'] == 150 for res_capacity in data['capacityPlan']['resourceCapacities'])

def test_delete_pillar_capacity_plan(app):
    with app.app_context():
        # Call the helper function to create the baseline ZBB.
        baseline_zbb_ids = create_baseline_zbb()

        # Use the returned IDs directly
        pillar_id = baseline_zbb_ids['pillar_id']
        capacity_plan_id = baseline_zbb_ids['capacity_plan_id']

        with app.test_client() as client:
            # Execute a DELETE request
            response = client.delete(f'/pillars/{pillar_id}/capacity_plans/{capacity_plan_id}')

            # Check the response status code
            assert response.status_code == 200

            # Fetch the deleted capacity plan from the database
            deleted_capacity_plan = CapacityPlan.query.get(capacity_plan_id)

            # Check if the capacity plan has been deleted
            assert deleted_capacity_plan is None
