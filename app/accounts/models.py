from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,AbstractUser
from .manage import UserManager
# class CustomUser(AbstractUser):
#     pass

class User(AbstractBaseUser, PermissionsMixin):
    CARGO_CHOICES=(('Lider','LIDER'),('Tester','TESTER'))
    EQUIPO_CHOICES=(
    ('Claro TV STB - IPTV - Roku - TATA','Claro TV STB - IPTV - Roku - TATA'),
    ('STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)','STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)'),
    ('IPTV AOSP','IPTV AOSP'),
    ('WIN - WEB - Fire TV','WIN - WEB - Fire TV'),
    ('IOS - TvOS','IOS - TvOS'),
    ('Android','Android'),
    ('Smart TV AAF','Smart TV AAF')
    )
    username = models.CharField(max_length=15, unique=True)
    nombre = models.CharField('Nombre(s)', max_length=20)
    apellido = models.CharField('Apellido(s)', max_length=30)
    cargo=models.CharField('Cargo',choices=CARGO_CHOICES,default='Tester')
    equipo=models.CharField('Equipo',choices=EQUIPO_CHOICES,null=True,blank=True)
    is_staff = models.BooleanField(default=False)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        

    def __str__(self):
        return f'{self.nombre} {self.apellido}'
