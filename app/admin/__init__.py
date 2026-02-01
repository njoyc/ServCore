from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from app.admin import routes
from app.admin.utils import admin_context_processor


@admin_bp.app_context_processor
def inject_admin_data():
    return admin_context_processor()
