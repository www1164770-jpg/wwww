"""Hand-labelled synthetic resources; relevance labels are independent of ranker."""
def resources():
    result=[]
    for sid in range(1,13):
        paper=sid in {1,2,3,4,10,11,12}
        tags=['student','research','literature_search'] if paper else ['developer','backend','api_debugging']
        if sid==9:tags=['shopping']
        tags=tags+(['annotation'] if sid in {3,7} else ['reference_export'] if sid in {4,8} else [])
        result.append({'id':sid,'name':f'Fixture {sid:02d}','url':f'https://source{sid if sid in {3,4,7,8} else 1}.invalid/products/{sid}',
            'tags':tags,'occupations':['student' if paper else 'developer'],'category_id':2 if sid in {3,7} else 3 if sid in {4,8} else 1,
            'status':'approved','enabled':0 if sid==10 else 1,'summary':'文献检索' if paper else '接口调试' if sid!=9 else '购物',
            'quality_score':100 if sid in {1,2,5,6} else 80,'created_at':'2020-01-01',
            'canonical_site_id':1 if sid==2 else 5 if sid==6 else sid,
            'hard_constraints_met':sid not in {11,12}})
    return result

PROFILES=[{'name':'literature','profile':{'occupation':'student','direction':'research','primary_need':'literature_search'},'relevant_ids':{1,2,3,4},'product_ids':{1:1,2:1,3:3,4:4}},
          {'name':'api','profile':{'occupation':'developer','direction':'backend','primary_need':'api_debugging'},'relevant_ids':{5,6,7,8},'product_ids':{5:5,6:5,7:7,8:8}}]
# Independent annotations used by the evaluator, not the diversity feature function.
TASKS={1:{'find'},2:{'find'},3:{'find','annotate'},4:{'find','export'},5:{'request'},6:{'request'},7:{'request','mock'},8:{'request','document'}}
TYPES={1:'search',2:'search',3:'workspace',4:'reference',5:'client',6:'client',7:'mock',8:'documentation'}
