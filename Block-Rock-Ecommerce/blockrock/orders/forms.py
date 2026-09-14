from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'shipping_name',
            'phone',
            'email',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
            'payment_method',
        ]
        labels = {
            'shipping_name': 'Full Name',
            'phone': 'Phone Number',
            'email': 'Email Address',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2 (Optional)',
            'city': 'City',
            'state': 'State / Province',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'payment_method': 'Payment Method',
        }
        widgets = {
            'shipping_name': forms.TextInput(attrs={'placeholder': 'e.g. Alex Mercer', 'class': 'form-control', 'required': 'required'}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g. +91 98765 43210', 'class': 'form-control', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'placeholder': 'e.g. alex@example.com', 'class': 'form-control', 'required': 'required'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street address, P.O. box', 'class': 'form-control', 'required': 'required'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Apartment, suite, unit (optional)', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'placeholder': 'e.g. Mumbai', 'class': 'form-control', 'required': 'required'}),
            'state': forms.TextInput(attrs={'placeholder': 'e.g. Maharashtra', 'class': 'form-control', 'required': 'required'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'e.g. 400001', 'class': 'form-control', 'required': 'required'}),
            'country': forms.TextInput(attrs={'placeholder': 'e.g. India', 'class': 'form-control', 'required': 'required'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_payment_method(self):
        method = self.cleaned_data.get('payment_method')
        if method != Order.PAYMENT_COD:
            raise forms.ValidationError('Selected payment method is currently unavailable.')
        return method
