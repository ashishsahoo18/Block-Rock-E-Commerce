from django.shortcuts import render

from .models import Product



def products(request):


    query = request.GET.get('search')


    if query:


        products = Product.objects.filter(

            name__icontains=query

        )


    else:


        products = Product.objects.all()



    return render(

        request,

        'products.html',

        {

            'products':products

        }

    )





def product_detail(request,id):


    product = Product.objects.get(id=id)


    return render(

        request,

        'product_detail.html',

        {

            'product':product

        }

    )