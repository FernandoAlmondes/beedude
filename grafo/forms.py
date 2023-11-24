from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)

    fields = ['username','password']
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)

        # Personaliza a mensagem de erro para o campo 'name'
        self.fields['username'].error_messages = {'required': 'O campo username é obrigatório.'}

        # Personaliza a mensagem de erro para o campo 'email'
        self.fields['password'].error_messages = {'required': 'O campo senha é obrigatório.'}

        # Se você quiser personalizar a mensagem de erro para todos os campos
        for field_name, field in self.fields.items():
            field.error_messages = {'required': f'O campo {field_name} é obrigatório.'}