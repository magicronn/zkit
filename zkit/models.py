from binascii import a2b_base64
from email.policy import default
from os import name
from xml.dom.pulldom import END_DOCUMENT
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Plan(db.Model) :
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    startDate = db.Column(db.Date, nullable=True)
    endDate = db.Column(db.Date, nullable=True)
    cntSliceMonth = db.Column(db.Integer, nullable=True, default=1)
    cntSliceWeek = db.Column(db.Integer, nullable=True, default=0)
    cntSliceDay = db.Column(db.Integer, nullable=True, default=0)
    cntSlices = db.Column(db.Integer, nullable=False, default=12)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    pillar = db.Column(db.Integer, db.ForeignKey('pillar.id'), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String(24), nullable=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(8192), nullable=False)
    docLink = db.Column(db.String(512), nullable=True)
    parent = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    customers = db.Column(db.String(512), nullable=True)
    justification = db.Column(db.String(512), nullable=True)
    dueDate = db.Column(db.Date, nullable=True)
    programSpend = db.Column(db.Double, nullable=False, default=0.0)


class ProjectEstimate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    resType = db.Column(db.Integer, db.ForeignKey('resource_type.id'), nullable=False)
    estimate = db.Column(db.Integer, nullable=False)  # in planSlices
    

class Pillar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    abbreviation = db.Column(db.String(6), nullable=False)

        
# CapacityPlan is a resource capacity plan.  It contains an ordered list of ResourceCapacity for a plan, given that plan's cntSlices.
class CapacityPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)  # base or adjustment
    pillar = db.Column(db.Integer, db.ForeignKey('pillar.id'), nullable=False)
    

# ResourceCapacity is a resource capacity for a given resource type and a given plan slice. It belongs to a CapacityPlan. 
class ResourceCapacity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    capacityPlan = db.Column(db.Integer, db.ForeignKey('capacity_plan.id'), nullable=False)
    resType = db.Column(db.Integer, db.ForeignKey('resource_type.id'), nullable=False)
    planSlice = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)


# ResourceType is an enumeration of the resource types, e.g. "Developer", "TPM", "ProdMgr", etc.
class ResourceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    abbreviation = db.Column(db.String(6), nullable=False)
    

class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False)
    project = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    deliverySlice = db.Column(db.Integer, nullable=False)
    deliveredFlag = db.Column(db.Boolean, nullable=False, default=False)
    startDate = db.Column(db.Date, nullable=True)
    endDate = db.Column(db.Date, nullable=True)


