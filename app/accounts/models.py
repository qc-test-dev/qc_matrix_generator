from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,AbstractUser
from .manage import UserManager
# class CustomUser(AbstractUser):
#     pass

class User(AbstractBaseUser, PermissionsMixin):
    CARGO_CHOICES=(('Lider','LIDER'),('Tester','TESTER'))
    EQUIPO_CHOICES=(
    ('Roku','Roku'),
    ('STV(TATA)','STV(TATA)'),
    ('STB','STB'),
    ('WEB','WEB'),
    ('IOS','IOS')
    )
    username = models.CharField(max_length=15, unique=True)
    nombre = models.CharField('Nombre(s)', max_length=20)
    apellido = models.CharField('Apellido(s)', max_length=30)
    cargo=models.CharField('Cargo',choices=CARGO_CHOICES,default='Tester')
    equipo=models.CharField('Equipo',choices=EQUIPO_CHOICES,default='STB')
    is_staff = models.BooleanField(default=False)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.nombre} {self.apellido}'
