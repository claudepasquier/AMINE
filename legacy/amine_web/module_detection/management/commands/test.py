from django.db import models
from django.core.management.base import BaseCommand, CommandError
from module_detection.models import Genedata
import time

class Command(BaseCommand):
    help = 'executes the module_detection programm'

    def add_arguments(self, parser):
        parser.add_argument('arg_filename', nargs='+', type=str)

    def handle(self, *args, **options):
        for bdd_filename in options['arg_filename']:
            try:
                bdd_res = Genedata.objects.get(filename=bdd_filename)
            except Genedata.DoesNotExist:
                raise CommandError('failed, "%s" does not exist' % bdd_filename)

            bdd_res.processing_done = True

            # For test purposes
            time.sleep(60)


            bdd_res.save()
