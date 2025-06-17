from django.contrib.auth.base_user import BaseUserManager
from django.db import models
class UserManager(BaseUserManager,models.Manager):
    def _create_user(self, username, nombre, apellido,password,is_staff,is_superuser, **extra_fields):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        user = self.model(
            username=username,
            nombre=nombre, 
            apellido=apellido,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra_fields
            )
        user.set_password(password)
        user.save(using=self.db)
        return user
    def create_user(self,username, nombre, apellido,password,**extra_fields):
        return self._create_user(username, nombre, apellido, password,False,False, **extra_fields)
        
    def create_superuser(self, username, nombre, apellido, password=None, **extra_fields):
        return self._create_user(username, nombre, apellido, password,True,True, **extra_fields)
