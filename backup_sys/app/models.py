import os
import sqlalchemy as sa
from flask_login import UserMixin
from app import db, app
# from users_policy import UserPolicy
from werkzeug.security import check_password_hash, generate_password_hash
from flask import url_for

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'))
    
    role = db.relationship('Role')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return ' '.join([self.last_name, self.first_name, self.middle_name or ''])

    @property
    def is_admin(self):
        return app.config.get('ADMIN_ROLE_ID') == self.role_id

    @property
    def is_moder(self):
        return app.config.get('MODER_ROLE_ID') == self.role_id

    @property
    def is_user(self):
        return app.config.get('USER_ROLE_ID') == self.role_id

    # def can(self, action):
    #     user_policy = UserPolicy()
    #     method = getattr(user_policy, action) 
    #     if method is not None:
    #         return method()
    #     return False


    def __repr__(self):
        return '<Users  %r>' % self.login

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), nullable=False)
    role_description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return '<Role %r>' % self.role_name
    
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    vendor = db.Column(db.String(50), nullable=False)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    login = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    backup_date = db.Column(db.Date)
    is_online = db.Column(db.Boolean)
    auto_backup = db.Column(db.Boolean)

    def __repr__(self):
        return '<Device %r>' % self.hostname
