from django.db import models
from django.utils import timezone

class Querydata(models.Model):
    SPECIE_CHOICES = (
    ('Hs', 'Homo sapiens'),
    ('Mm','Mus musculus'),
    ('Dm','Drosophila melanogaster'),
    ('Ce','Caenorhabditis elegans'),
    )

    AGG_METHOD_CHOICES = (
    ('pvalue', 'pvalue'),
    ('log2fc', 'log2fc'),
    ('pivalue', 'pivalue (pvalue & log2fc)'),
    )

    job_title = models.CharField(max_length=50, default='default_job_title')
    query_id = models.CharField(max_length=100)
    file = models.FileField(upload_to='./module_detection/')
    file_gene_col = models.IntegerField()
    aggregation_method = models.CharField(max_length=7, choices=AGG_METHOD_CHOICES, default=AGG_METHOD_CHOICES[0][0])
    file_pvalue_col = models.IntegerField()
    file_log2fc_col = models.IntegerField(default=0)
    interest_gene_file = models.FileField(upload_to='./module_detection/interest_gene/',default='',blank=True)
    module_nb = 9 # default value instead of models.IntegerField()
    specie = models.CharField(max_length=2, choices=SPECIE_CHOICES, default=SPECIE_CHOICES[0][0])
    email = models.EmailField(default='',blank=True)
    crea_date = models.DateTimeField('Date of creation',default=timezone.now)
    queue_pos = models.IntegerField(default=0)
    processing_done = models.BooleanField(default=False)
    job_success = models.BooleanField(default=False)

    def __str__(self):
        return self.query_id

class Modules_result(models.Model):
    module_id = models.CharField(max_length=50)
    module_query = models.ForeignKey(Querydata, on_delete=models.CASCADE)
    score = models.FloatField()

    def __str__(self):
        return self.module_id

class Gene(models.Model):
    gene_id = models.CharField(max_length=15)
    gene_query = models.ManyToManyField(Modules_result)

    def __str__(self):
        return self.gene_id
