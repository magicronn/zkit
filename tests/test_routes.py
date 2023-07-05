import pytest
from datetime import datetime
from zkit.models import Plan, db

def test_get_plan(app):
    with app.app_context():
        with app.test_client() as client:
            # Your test code here
            # Arrange: Add a plan to the database
            plan = Plan(
                name='Test Plan', 
                startDate=datetime.now(), 
                endDate=datetime.now(),
                cntSliceMonth=1,
                cntSliceWeek=0,
                cntSliceDay=0,
                cntSlices=12,
            )
            db.session.add(plan)
            db.session.commit()

            # Act: Send a GET request to /plans/<id>
            response = client.get(f'/plans/{plan.id}')

            # Assert: Check the response data
            assert response.status_code == 200
            assert response.get_json()['name'] == 'Test Plan'
