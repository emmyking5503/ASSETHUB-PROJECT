from django import forms
from .models import Review, Dispute


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your review here...'
            }),
        }


class DisputeForm(forms.ModelForm):
    """Form for buyer to submit a new dispute"""
    
    declaration = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must confirm that all information is accurate.'}
    )

    class Meta:
        model = Dispute
        fields = ['reason', 'complaint', 'requested_resolution']
        widgets = {
            'reason': forms.RadioSelect(attrs={'class': 'd-none'}),
            'complaint': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe the issue in detail...'
            }),
            'requested_resolution': forms.RadioSelect(attrs={'class': 'd-none'}),
        }

    def clean_complaint(self):
        complaint = self.cleaned_data.get('complaint')
        if not complaint or len(complaint.strip()) < 20:
            raise forms.ValidationError("Please provide a detailed description (at least 20 characters).")
        return complaint.strip()


class DisputeResponseForm(forms.Form):
    """Form for seller to respond to a dispute"""
    
    seller_response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Explain your side of the case in detail...'
        }),
        required=True
    )
    seller_courier = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Courier Company'
        })
    )
    seller_tracking = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tracking Number'
        })
    )
    seller_ship_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    seller_delivery_confirm = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Delivery Confirmation'
        })
    )
    declaration = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must confirm that your response is accurate.'}
    )

    def clean_seller_response(self):
        response = self.cleaned_data.get('seller_response')
        if not response or len(response.strip()) < 20:
            raise forms.ValidationError("Please provide a detailed response (at least 20 characters).")
        return response.strip()


class BuyerReplyForm(forms.Form):
    """Form for buyer to reply after seller response"""
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Add your reply or additional information...'
        }),
        required=True
    )

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if not message or len(message.strip()) < 10:
            raise forms.ValidationError("Please provide a meaningful reply (at least 10 characters).")
        return message.strip()


class AdminDecisionForm(forms.Form):
    """Form for admin to make final decision"""
    
    DECISION_CHOICES = [
        ('resolved_buyer', 'Resolve in Favor of Buyer (Refund)'),
        ('resolved_seller', 'Resolve in Favor of Seller (Release Escrow)'),
        ('resolved_mutual', 'Mutual Agreement'),
        ('more_info', 'Request More Information'),
        ('return_required', 'Require Buyer to Return Item'),
    ]

    decision = forms.ChoiceField(
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    admin_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Add your notes and reasoning...'
        }),
        required=True
    )

    def clean_admin_notes(self):
        notes = self.cleaned_data.get('admin_notes')
        if not notes or len(notes.strip()) < 10:
            raise forms.ValidationError("Please provide detailed reasoning for your decision.")
        return notes.strip()

class ReturnTrackingForm(forms.Form):
    """Buyer submits return tracking — courier is free text input."""
    return_courier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter courier company name (e.g. FedEx, DHL, local courier...)'
        }),
        label='Courier Service'
    )
    return_tracking = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. FX-1234567890'
        }),
        label='Tracking Number'
    )
    
    