from django import forms
from .models import Querydata

class QuerydataForm(forms.ModelForm):

    class Meta:
        model = Querydata
        fields = ('job_title','file','email','specie','file_gene_col','file_pvalue_col','interest_gene_file','file_log2fc_col')

