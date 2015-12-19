import json
import collections
import sys
# import pexpect

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from bq_data_access.feature_search.util import SearchableFieldHelper
from models import Variable, VariableFavorite
from django.core.urlresolvers import reverse
from google.appengine.api import urlfetch
from django.conf import settings
debug = settings.DEBUG
from django.http import HttpResponse

urlfetch.set_default_fetch_deadline(60)
BIG_QUERY_API_URL   = settings.BASE_API_URL + '/_ah/api/bq_api/v1'
COHORT_API          = settings.BASE_API_URL + '/_ah/api/cohort_api/v1'
META_DISCOVERY_URL  = settings.BASE_API_URL + '/_ah/api/discovery/v1/apis/meta_api/v1/rest'
METADATA_API        = settings.BASE_API_URL + '/_ah/api/meta_api/v1'

# tests whether parameter is a string, hash or iterable object
# then returns base type data
def convert(data):
    #if debug: print >> sys.stderr,'Called '+sys._getframe().f_code.co_name
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data

# sorts on availability of a key in the feature def table?
def data_availability_sort(key, value, data_attr, attr_details):
    #if debug: print >> sys.stderr,'Called '+sys._getframe().f_code.co_name

    if key == 'has_Illumina_DNASeq':
        attr_details['DNA_sequencing'] = sorted(value, key=lambda k: int(k['count']), reverse=True)
    if key == 'has_SNP6':
        attr_details['SNP_CN'] = sorted(value, key=lambda k: int(k['count']), reverse=True)
    if key == 'has_RPPA':
        attr_details['Protein'] = sorted(value, key=lambda k: int(k['count']), reverse=True)
    if key == 'has_27k':
        attr_details['DNA_methylation'].append({
            'value': '27k',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_450k':
        attr_details['DNA_methylation'].append({
            'value': '450k',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_HiSeq_miRnaSeq':
        attr_details['miRNA_sequencing'].append({
            'value': 'Illumina HiSeq',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_GA_miRNASeq':
        attr_details['miRNA_sequencing'].append({
            'value': 'Illumina GA',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_UNC_HiSeq_RNASeq':
        attr_details['RNA_sequencing'].append({
            'value': 'UNC Illumina HiSeq',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_UNC_GA_RNASeq':
        attr_details['RNA_sequencing'].append({
            'value': 'UNC Illumina GA',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_BCGSC_HiSeq_RNASeq':
        attr_details['RNA_sequencing'].append({
            'value': 'BCGSC Illumina HiSeq',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })
    if key == 'has_BCGSC_GA_RNASeq':
        attr_details['RNA_sequencing'].append({
            'value': 'BCGSC Illumina GA',
            'count': [v['count'] for v in value if v['value'] == 'True'][0]
        })

@login_required
def variable_fav_detail(request, variable_fav_id):
    # """ if debug: print >> sys.stderr,'Called '+sys._getframe().f_code.co_name """
    template = 'variables/variable_detail.html'
    context = {
        'variables': {
            'name': 'My Favorite Variables',
            'list': [{
                'parent': 'Gender',
                'identifier': 'Female'
            },{
                'parent': ''
            }]
        }
    }
    return render(request, template, context)

@login_required
def variable_fav_create(request):
    template = 'variables/variable_edit.html'

    if debug: print >> sys.stderr,'Called '+sys._getframe().f_code.co_name
    users = User.objects.filter(is_superuser=0)

    # service = build('meta', 'v1', discoveryServiceUrl=META_DISCOVERY_URL)
    # clin_attr = [
    #     'vital_status',
    #     # 'survival_time',
    #     'gender',
    #     'age_at_initial_pathologic_diagnosis',
    #     'SampleTypeCode',
    #     'tumor_tissue_site',
    #     'histological_type',
    #     'prior_dx',
    #     'pathologic_stage',
    #     'person_neoplasm_cancer_status',
    #     'new_tumor_event_after_initial_treatment',
    #     'neoplasm_histologic_grade',
    #     # 'bmi',
    #     'residual_tumor',
    #     # 'targeted_molecular_therapy', TODO: Add to metadata_samples
    #     'tobacco_smoking_history',
    #     'icd_10',
    #     'icd_o_3_site',
    #     'icd_o_3_histology'
    # ]

    # data_attr = [
    #     'has_Illumina_DNASeq',
    #     'has_BCGSC_HiSeq_RNASeq',
    #     'has_UNC_HiSeq_RNASeq',
    #     'has_BCGSC_GA_RNASeq',
    #     'has_UNC_GA_RNASeq',
    #     'has_HiSeq_miRnaSeq',
    #     'has_GA_miRNASeq',
    #     'has_RPPA',
    #     'has_SNP6',
    #     'has_27k',
    #     'has_450k'
    # ]

    data_attr = [
        'DNA_sequencing',
        'RNA_sequencing',
        'miRNA_sequencing',
        'Protein',
        'SNP_CN',
        'DNA_methylation'
    ]
    #
    # molec_attr = [
    #     'somatic_mutation_status',
    #     'mRNA_expression',
    #     'miRNA_expression',
    #     'DNA_methylation',
    #     'gene_copy_number',
    #     'protein_quantification'
    # ]

    # This is a list of specific data classifications which require additional filtering in order to
    # Gather categorical or numercial variables for use in the plot
    # Filter Options
    datatype_labels = {'CLIN' : 'Clinical',
                       'GEXP' : 'Gene Expression',
                       'MIRN' : 'miRNA',
                       'METH' : 'Methylation',
                       'CNVR' : 'Copy Number',
                       'RPPA' : 'Protein',
                       'GNAB' : 'Mutation'}

    datatype_list = SearchableFieldHelper.get_fields_for_all_datatypes()
    for type in datatype_list:
        type['label'] = datatype_labels[type['datatype']]

        #remove gene in fields
        if debug: print >> sys.stderr, ' attrs ' + json.dumps(type['fields'])
        for index, field in enumerate(type['fields']):
            if field['label'] == "Gene":
                del type['fields'][index]

    #stub
    study_name_list = {
        "Project 1 : study 1" : ["variable1", "variable2"],
        "Project 2 : study 2" : ["variable1", "variable2"],
        "Project 3 : study 3" : ["variable1", "variable2"],
    }

    #stubbed data for populating the variable list model
    TCGA_project    = {"id" : -1, "study" : {"id" :-1, "name" : ""}, "name" : "TCGA"};
    common_project  = {"id" : -1, "study" : {"id" :-1, "name" : ""}, "variables" : ["Gender", "Sex", "Height", "Weight"], "name" : "Common"};

    data_url = METADATA_API + '/metadata_counts?'
    results = urlfetch.fetch(data_url, deadline=60)
    results = json.loads(results.content)
    totals  = results['total']

    #Get and sort counts
    variable_list = convert(results['count'])
    variable_list['RNA_sequencing'] = []
    variable_list['miRNA_sequencing'] = []
    variable_list['DNA_methylation'] = []
    for key, value in variable_list.items():
        if key.startswith('has_'):
            data_availability_sort(key, value, data_attr, variable_list)
        else:
            variable_list[key] = sorted(value, key=lambda k: int(k['count']), reverse=True)

    template_values = {
        'variable_names'        : variable_list.keys(),
        'variable_list_count'   : variable_list,
        'datatype_list'         : datatype_list,
        'study_name_list'       : study_name_list,

        # 'clinical_variables'    : clin_attr,
        'data_attr'             : data_attr,
        'total_samples'         : totals,

        'base_url'              : settings.BASE_URL,
        'base_api_url'          : settings.BASE_API_URL,
        'TCGA_project'          : TCGA_project,
        'common_project'        : common_project
    }

    if debug: print >> sys.stderr, ' attrs ' + json.dumps(datatype_list)

    return render(request, template, template_values)

@login_required
def variable_fav_list(request):
    template = 'variables/variable_list.html'
    variable_list = VariableFavorite.get_list(request.user)

    return render(request, template, {'variable_list' : variable_list})

@login_required
def variable_fav_edit(request, variable_fav_id):
    template = 'variables/variable_edit.html'
    context = {}
    return render(request, template, context)

@login_required
def variable_delete(request, variable_fav_id):
    return render(request, template, context)

@login_required
def variable_share(request, variable_fav_id):
    return render(request, template, context)

@login_required
def variable_copy(request, variable_fav_id):
    return render(request, template, context)

@login_required
def variable_save(request):
    data = json.loads(request.body)
    variable_model = VariableFavorite.create(name       =data['name'],
                                            variables   =data['variables'],
                                            user        =request.user)
    return HttpResponse(json.dumps(variable_model), status=200)