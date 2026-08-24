from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False, max_length=20)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "phone", "password1", "password2")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone", "avatar", "bio", "location")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell people about yourself..."}),
            "location": forms.TextInput(attrs={"placeholder": "City, Country"}),
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "avatar":
                field.widget.attrs.update({
                    "class": "w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:ring-2 focus:ring-gray-500 focus:border-gray-500 transition-all"
                })
        self.fields["avatar"].widget.attrs.update({
            "class": "w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
        })