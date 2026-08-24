from django import forms
from .models import Livestock


class LivestockForm(forms.ModelForm):
    class Meta:
        model = Livestock
        fields = [
            "title", "category", "description", "price", "breed",
            "age", "weight_kg", "location", "status", "whatsapp_number",
            "image_1", "image_2", "image_3",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    base_input_class = (
        "w-full border border-gray-300 rounded-lg p-2.5 "
        "focus:ring-2 focus:ring-green-600 focus:border-green-600"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields explicit
        required_fields = ['title', 'category', 'description', 'price', 'location', 'whatsapp_number', 'image_1']
        for name, field in self.fields.items():
            if name in required_fields:
                field.required = True
            # image_2 and image_3 are optional
            if name in ['image_2', 'image_3']:
                field.required = False
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {self.base_input_class}".strip()
