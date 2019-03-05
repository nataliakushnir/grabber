from django.db import models

# Create your models here.
from simple_history.models import HistoricalRecords


class Product(models.Model):
    name = models.CharField('Name or title', max_length=255)
    description = models.TextField('Description')
    code = models.CharField('Product code', max_length=15)

    available_price = models.DecimalField('Available price', max_digits=10, decimal_places=2, blank=True, null=True)
    old_price = models.DecimalField('Old price', max_digits=10, decimal_places=2, blank=True, null=True)

    is_available = models.BooleanField('Is available', default=True)

    history = HistoricalRecords(inherit=True, cascade_delete_history=True)
    created_on = models.DateTimeField('Created date', auto_now_add=True, blank=False)
    last_modified = models.DateTimeField('Last modified', auto_now=True, blank=False)

    def __str__(self):
        return self.name


class ProductImageManager(models.Manager):
    def get_main_or_first(self):
        """
        Does not contain filtering by product, so
        to be used with a product.images reverse manager to get image of particular product.
        """
        qs = self.filter(is_main=True)
        if qs.exists():
            return qs.first()
        else:
            return self.first()


def upload_to_code_product(instance, filename):
    """
    Method returns the upload_to path for the Product images.
    """

    PRODUCTS_ROOT_FOLDER = 'products'

    product_id_folder = instance.product.code

    filename_clean = '/'.join([
        PRODUCTS_ROOT_FOLDER, product_id_folder,
        filename.lstrip('/')
    ])

    filename_clean.lstrip('/')
    return filename_clean


class ProductImage(models.Model):
    image = models.ImageField(upload_to=upload_to_code_product, max_length=255)
    product = models.ForeignKey(
        Product, related_name='images', blank=False, null=False, on_delete=True)
    hash = models.CharField('Image hash', max_length=30)
    is_main = models.BooleanField("Is main?", default=False)

    timestamp = models.DateTimeField(auto_now_add=True)

    objects = ProductImageManager()

    def __str__(self):
        return f'{self.product.code}'
