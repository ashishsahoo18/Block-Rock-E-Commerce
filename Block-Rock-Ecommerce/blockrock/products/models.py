from django.db import models


class Product(models.Model):

    name = models.CharField(max_length=200)

    description = models.TextField()

    price = models.IntegerField()

    discount = models.IntegerField(default=0)

    category = models.CharField(max_length=100)

    brand = models.CharField(max_length=100)

    stock = models.IntegerField(default=0)

    rating = models.FloatField(default=0)

    image = models.ImageField(upload_to='products/')


    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):

        return self.name