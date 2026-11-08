from huey.contrib.djhuey import task, db_task
from module_detection.models import Querydata, Modules_result, Gene
from .module_detection_core.process_real_network_web import process
from django.core.mail import send_mail
from decouple import config
import traceback


@db_task()
def module_detection_run(query_id, job_title, file, email, specie, module_nb, gene_col, pvalue_col, log2fc_col, output_files, focusGene_file, aggregation_method="pvalue"):

    admin = config('ADMIN_MAIL')

    print("########################## Huey start run")

###### Mail temp ok ######
    mailbody_verif = 'AMINE : Job start.\n\n New job launched ' + query_id + '\n\nThis is an automated mail, please do not reply.'

#    send_mail(
#        'AMINE -- Job started',
#        mailbody_verif,
#        'amine.webmail@i3s.unice.fr',
#        admin,
#        fail_silently=False,
#        )
#####################################

    species_list = {'Hs' : 'human','Ce' : 'caenorhabditis', 'Mm' : 'mouse', 'Dm' : 'drosophila'}
    species_file = species_list[specie]

    #python's counting way
    gene_col -= 1
    pvalue_col -= 1
    log2fc_col -= 1

    if pvalue_col < 0 :
        pvalue_col = None
    if log2fc_col < 0 :
        log2fc_col = None

    print("file : " + str(file))


    try:
        result_run = process(file, module_nb, species_file, gene_col, log2fc_col, pvalue_col, output_files, focusGene_file, aggregation_method)

        print('##########################################result_run##########################################')
        print(result_run)


        querydata_res = Querydata.objects.get(query_id=query_id)

        for module in result_run :

            i = module[0]
            id = query_id + '_' + str(i)

            module_res = Modules_result(module_id=id, module_query=querydata_res, score=module[-1])
            module_res.save()

            print(module_res)

            for result_run_genes in module[1].split(',') :
                gene_res, created = Gene.objects.get_or_create(gene_id=result_run_genes)
                gene_res.gene_query.add(module_res)


        querydata_res.processing_done = True
        querydata_res.job_success = True
        querydata_res.save()

        print("########################## Huey run complete")

        if email :

            mailbody = 'amine : Your job ' + str(job_title) + ' is complete.\n\nYou can find your results by clicking the link below\nhttp://134.59.130.160/results/' + str(query_id) + '/\nOr by visiting or refreshing your result page.\n\n\nJob informations :\n  File : ' + str(file.split('/')[-1].split('_')[0]) + '\n  Specie : ' + str(species_file) + '\n  Number of modules : ' + str(module_nb) + '\n  Column with gene names : ' + str(gene_col+1) + '\n  Column with p-values : ' + str(pvalue_col+1)

            if log2fc_col :
                mailbody += '\n  Column with log2 fold change : ' + str(log2fc_col+1)
            if focusGene_file :
                mailbody += '\n  File with favorite genes : ' + str(focusGene_file)

            mailbody += '\n\nThank you\n\nThis is an automated mail, please do not reply.'

            send_mail(
                'amine : Your results for the job ' + job_title + ' are ready',
                mailbody,
                'amine.webmail@i3s.unice.fr',
                [email],
                fail_silently=False,
                )


###### Mail temp ok ######
#    mailbody_verif = 'AMINE : Job complete.\n\nYou can find your results by clicking the link below\nhttp://134.59.130.160/results/' + query_id + '/\nOr by visiting or refreshing your result page.\nThank you\n\nThis is an automated mail, please do not reply.'

#    send_mail(
#        'AMINE -- Job complete',
#        mailbody_verif,
#        'amine.webmail@i3s.unice.fr',
#        admin,
#        fail_silently=False,
#        )
#####################################
    except Exception :
        traceback.print_exc()

        print("Job failed " + query_id)

        querydata_res = Querydata.objects.get(query_id=query_id)
        querydata_res.processing_done = True
        querydata_res.save()

        if email:
            mailbody = 'AMINE : Your job ' + query_id + ' failed.\n\nPlease verify your input and contact an administrator.\n\nThis is an automated mail, please do not reply.'

            send_mail(
                'AMINE -- Job failed',
                mailbody,
                'amine.webmail@i3s.unice.fr',
                [email],
                fail_silently=False,
                )
#
#
###### Mail temp fail ######
#        mailbody = 'AMINE : Job failed.\n\n' + query_id + '/\n\nThis is an automated mail, please do not reply.'
#
#        send_mail(
#        'AMINE -- Job failed',
#        mailbody_verif,
#        'amine.webmail@i3s.unice.fr',
#        admin,
#        fail_silently=False,
#        )
#####################################


