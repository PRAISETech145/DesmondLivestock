from django import forms
from .models import Post, Comment, Topic


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["topic", "title", "content", "image"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Share your farming challenges, ideas, or experiences..."
            }),
            "title": forms.TextInput(attrs={
                "placeholder": "Optional title (e.g., 'Need help with tomato blight')"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topic"].empty_label = "Select a topic (optional)"
        self.fields["topic"].required = False
        for name, field in self.fields.items():
            if name != "image":
                field.widget.attrs.update({
                    "class": "w-full border border-gray-300 rounded-xl px-4 py-3 text-gray-900 focus:ring-2 focus:ring-green-600 focus:border-green-600 transition-all"
                })
        self.fields["image"].widget.attrs.update({
            "class": "w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-medium file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
        })


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Write a reply...",
                "class": "w-full border border-gray-200 rounded-xl px-4 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-all resize-none"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].label = ""


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["name", "description", "icon", "order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "icon": forms.TextInput(attrs={"placeholder": "🌱 or emoji/icon"}),
        }