from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import Querydata, Modules_result, Gene
from .forms import QuerydataForm
from .tasks import module_detection_run
from datetime import datetime
import mimetypes

def index(request):
    form = QuerydataForm(request.POST or None, request.FILES)
    if form.is_valid():
        data = form.save(commit=False)
        time = datetime.now()
        data.query_id = str(data.file).replace(' ','_').split('.')[0] + '_' + str(time.hour) + str(time.minute) + str(time.second)
        data.save()
        redirect_url = 'results/' + data.query_id
        datafile_path = "module_detection/uploaded_files/" + str(data.file)
        outputfile_path = "static/module_detection/output_files/" + data.query_id + ".xlsx"
        
        if data.interest_gene_file :
            favoriteGenes_path = "module_detection/uploaded_files/" + str(data.interest_gene_file)
        else :
            favoriteGenes_path = None

        module_detection_run(data.query_id, data.job_title, datafile_path, data.email, data.specie, 9, data.file_gene_col, data.file_pvalue_col, data.file_log2fc_col, outputfile_path,favoriteGenes_path)

        return HttpResponseRedirect(redirect_url)
    else :
        return render(request, 'module_detection/index.html', locals())




def results(request, query_id):
    db_result = get_object_or_404(Querydata, query_id=query_id)
    show_result = db_result.email
    processed = db_result.processing_done
    job_success = db_result.job_success
    time = datetime.now()
    if processed == True :
        list_results = []
        module_nb = 0
        input_file_path = str(db_result.file).split("/")[1]
        input_file_ext = input_file_path.rsplit(".")[1]
        input_file = input_file_path.rsplit("_",1)[0]
        input_job_title = db_result.job_title
        input_gene_col = db_result.file_gene_col
        input_pvalue_col = db_result.file_pvalue_col
        input_specie = db_result.specie
        for module in Modules_result.objects.filter(module_query__query_id=query_id):
            res_gene = []
            module_nb += 1
            module_txt = 'Module : ' + str(module_nb)
            res_gene.append(module_txt)
            score_verb = "P-value : " + str('{:0.3e}'.format(module.score))
            res_gene.append(score_verb)
            for gene in Gene.objects.filter(gene_query__module_id=module) :
                res_gene.append(gene.gene_id)
            list_results.append(res_gene)
    else :
        process_pending = (Querydata.objects.filter(processing_done=False).count())-1
        process_time = db_result.crea_date.hour + process_pending + 3
        time_to_results = process_time - time.hour
    return render(request, 'module_detection/results.html', locals())


def download_file(request, query_id):
    fl_path = "static/module_detection/output_files/" + query_id + ".xlsx"
    filename = 'amine_results.xlsx'

    fl = open(fl_path, 'rb')
    response = HttpResponse(fl, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = "attachment; filename=%s" % filename
    return response

#def results_module(request, module):
#    return render(request, 'module_detection/results.html', locals())


def about(request):
    return render(request, 'module_detection/about.html', locals())


def contact(request):
    return render(request, 'module_detection/contact.html', locals())
