'''
Akond Rahman 
May 03, 2021 
Code to detect security anti-patterns 
'''
import parser 
import constants 
import graphtaint 
import os 
import pandas as pd 

def getYAMLFiles(path_to_dir):
    valid_  = [] 
    for root_, dirs, files_ in os.walk( path_to_dir ):
       for file_ in files_:
           full_p_file = os.path.join(root_, file_)
           if(os.path.exists(full_p_file)):
             if (full_p_file.endswith( constants.YML_EXTENSION  )  or full_p_file.endswith( constants.YAML_EXTENSION  )  ):
               valid_.append(full_p_file)
    return valid_ 

def isValidUserName(uName): 
    valid = True
    if (isinstance( uName , str)  ): 
        if( any(z_ in uName for z_ in constants.FORBIDDEN_USER_NAMES )   ): 
            valid = False   
        else: 
            valid = True    
    else: 
        valid = False   
    return valid

def isValidPasswordName(pName): 
    valid = True
    if (isinstance( pName , str)  ): 
        if( any(z_ in pName for z_ in constants.FORBIDDEN_PASS_NAMES) )  : 
            valid = False  
        else: 
            valid = True    
    else: 
        valid = False               
    return valid

def isValidKey(keyName): 
    valid = False 
    if ( isinstance( keyName, str )  ):
        if( any(z_ in keyName for z_ in constants.LEGIT_KEY_NAMES ) ) : 
            valid = True   
        else: 
            valid = False     
    else: 
        valid = False                      
    return valid    

def checkIfValidSecret(single_config_val):
    flag2Ret = False 
    # print(type( single_config_val ), single_config_val  )
    if ( isinstance( single_config_val, str ) ):
        single_config_val = single_config_val.lower()
        config_val = single_config_val.strip() 
        if ( any(x_ in config_val for x_ in constants.INVALID_SECRET_CONFIG_VALUES ) ):
            flag2Ret = False 
        else:
            if(  len(config_val) > 2 )  :
                flag2Ret = True 
    else: 
        flag2Ret = False 
    return flag2Ret

def scanUserName(k_ , val_lis ):
    hard_coded_unames = []
    if isinstance(k_, str):
        k_ = k_.lower()    
    # print('INSPECTING:', k_) 
    if( isValidUserName( k_ )   and any(x_ in k_ for x_ in constants.SECRET_USER_LIST )  ):
        # print( val_lis ) 
        for val_ in val_lis:
            if (checkIfValidSecret( val_ ) ): 
                # print(val_) 
                hard_coded_unames.append( val_ )
    return hard_coded_unames

def scanPasswords(k_ , val_lis ):
    hard_coded_pwds = []
    if isinstance(k_, str):
        k_ = k_.lower()    
    if( isValidPasswordName( k_ )   and any(x_ in k_ for x_ in constants.SECRET_PASSWORD_LIST )  ):
        for val_ in val_lis:
            if (checkIfValidSecret( val_ ) ): 
                hard_coded_pwds.append( val_ )
    return hard_coded_pwds


def checkIfValidKeyValue(single_config_val):
    flag2Ret = False 
    if ( isinstance( single_config_val, str ) ):
        if ( any(x_ in single_config_val for x_ in constants.VALID_KEY_STRING ) ):
            flag2Ret = True 
    return flag2Ret

def scanKeys(k_, val_lis):
    hard_coded_keys = []
    if isinstance(k_, str):
        k_ = k_.lower()    
    if( isValidKey( k_ )    ):
        for val_ in val_lis:
            if (checkIfValidKeyValue( val_ ) ): 
                hard_coded_keys.append( val_ )
    return hard_coded_keys    


def scanForSecrets(yaml_d): 
    key_lis, dic2ret_secret   = [], {} 
    parser.getKeyRecursively( yaml_d, key_lis )
    '''
    if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
    as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
    '''    
    for key_data  in key_lis:
        key_     = key_data[0]
        value_list = [] 
        parser.getValsFromKey( yaml_d, key_ , value_list )
        unameList = scanUserName( key_, value_list  )
        # print(unameList)
        passwList = scanPasswords( key_, value_list  )
        keyList   = scanKeys( key_, value_list )
        # print(keyList)
        if( len(unameList) > 0  )  or ( len(passwList) > 0  ) or ( len(keyList) > 0  ) :
            dic2ret_secret[key_] =  ( unameList, passwList, keyList ) 
    return dic2ret_secret


def scanForOverPrivileges(script_path):
    key_count , privi_dict_return = 0, {} 
    kind_values = [] 
    checkVal = parser.checkIfValidK8SYaml( script_path )
    if(checkVal): 
        yaml_dict = parser.loadYAML( script_path )
        key_lis   = []
        parser.getKeyRecursively(yaml_dict, key_lis) 
        '''
        if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
        as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
        '''
        just_keys = [x_[0] for x_ in key_lis] 
        if ( constants.KIND_KEY_NAME in just_keys ):
            parser.getValsFromKey( yaml_dict, constants.KIND_KEY_NAME, kind_values )
        '''
        For the time being Kind:DeamonSet is not a legit sink because they do not directly provision deplyoments 
        '''
        if ( constants.PRIVI_KW in just_keys ) and ( constants.DEAMON_KW not in kind_values  ) :
            privilege_values = []
            parser.getValsFromKey( yaml_dict, constants.PRIVI_KW , privilege_values )
            # print(privilege_values) 
            for value_ in privilege_values:
                    if value_ == True: 
                        key_lis_holder = parser.keyMiner(yaml_dict, value_ ) 
                        if(constants.SPEC_KW in key_lis_holder) and (constants.CONTAINER_KW in key_lis_holder) and (constants.SECU_CONT_KW in key_lis_holder) and (constants.PRIVI_KW in key_lis_holder):
                            key_count += 1
                            privi_dict_return[key_count] = value_, key_lis_holder 
    return privi_dict_return 


def scanSingleManifest( path_to_script ):
    '''
    While it is named as `scanSingleManifest` 
    it can only do taint tracking for secrets and over privileges 
    '''
    checkVal = parser.checkIfValidK8SYaml( path_to_script )
    # print(checkVal) 
    # initializing 
    dict_secret = {} 
    yaml_dict = parser.loadYAML( path_to_script )
    if(checkVal): 
        dict_secret = scanForSecrets( yaml_dict )
    elif ( parser.checkIfValidHelm( path_to_script )) :
        dict_secret = scanForSecrets( yaml_dict )
    
    '''
    taint tracking zone for secret dictionary 
    '''
    # print(dict_secret)
    within_secret_, templ_secret_, valid_taint_secr  = graphtaint.mineSecretGraph(path_to_script, yaml_dict, dict_secret) 
    # print(within_secret_) 
    # print(templ_secret_) 
    # print(valid_taint_secr) 
    '''
    taint tracking for over privileges 
    '''
    valid_taint_privi  = scanForOverPrivileges( path_to_script )
    # print(valid_taint_privi) 

    return within_secret_, templ_secret_, valid_taint_secr, valid_taint_privi 


def scanForHTTP( path2script ):
    sh_files_configmaps = {} 
    http_count = 0 
    if parser.checkIfValidK8SYaml( path2script ) or parser.checkIfValidHelm( path2script ):
        yaml_d   = parser.loadYAML( path2script )
        all_vals = list (parser.getValuesRecursively( yaml_d )  )
        all_vals = [x_ for x_ in all_vals if isinstance(x_, str) ] 
        for val_ in all_vals:
            # if (constants.HTTP_KW in val_ ) and ( (constants.WWW_KW in val_) and (constants.ORG_KW in val_) ):
            if (constants.HTTP_KW in val_ ) :
                key_lis   = []
                parser.getKeyRecursively(yaml_d, key_lis) 
                '''
                if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
                as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
                '''
                just_keys = [x_[0] for x_ in key_lis] 
                if ( constants.SPEC_KW in just_keys ):
                    '''
                    this branch is for HTTP values coming from Deplyoment manifests  
                    '''                    
                    http_count += 1 
                    sh_files_configmaps[http_count] =  val_ 
                elif( parser.checkIfValidHelm( path2script ) ):
                    '''
                    this branch is for HTTP values coming from Values.yaml in HELM charts  
                    '''
                    http_count += 1 
                    matching_keys = parser.keyMiner(yaml_d, val_)
                    key_ = matching_keys[-1]  
                    infected_list = graphtaint.mineViolationGraph(path2script, yaml_d, val_, key_) 
                    sh_files_configmaps[http_count] = infected_list
                else: 
                    '''
                    this branch is for HTTP values coming from ConfigMaps 
                    '''                    
                    val_holder = [] 
                    parser.getValsFromKey(yaml_d, constants.KIND_KEY_NAME, val_holder)
                    if ( constants.CONFIGMAP_KW in val_holder ):
                        http_count += 1 
                        infected_list = graphtaint.getTaintsFromConfigMaps( path2script  ) 
                        sh_files_configmaps[http_count] = infected_list
                        # print('ASI_MAMA:', sh_files_configmaps) 
                        # print( val_holder )
                        # print(val_)
                        # print(just_keys)  
    
    # print(sh_files_configmaps) 
    return sh_files_configmaps 

def scanForMissingSecurityContext(path_scrpt):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_scrpt )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_scrpt )
        key_lis = [] 
        parser.getKeyRecursively(yaml_di, key_lis)
        yaml_values = list( parser.getValuesRecursively(yaml_di) )
        '''
        if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
        as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
        '''
        real_key_lis = [x_[0] for x_ in key_lis]
        # print(real_key_lis) 
        if (constants.SECU_CONT_KW  not in real_key_lis)  and ( constants.CONTAINER_KW in real_key_lis ): 
            occurrences = real_key_lis.count( constants.CONTAINER_KW )
            for _ in range( occurrences ):
                cnt += 1 
                prop_value = constants.YAML_SKIPPING_TEXT 
                if ( constants.DEPLOYMENT_KW in yaml_values ) : 
                    prop_value = constants.DEPLOYMENT_KW
                    lis.append( prop_value )
                elif ( constants.POD_KW in yaml_values ) :
                    prop_value = constants.POD_KW 
                    lis.append( prop_value )
                dic[ cnt ] = lis
    # print(dic) 
    return dic 


def scanForDefaultNamespace(path_scrpt):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_scrpt )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_scrpt )
        key_lis = parser.keyMiner(yaml_di, constants.DEFAULT_KW)
        if (isinstance( key_lis, list ) ):
            if (len(key_lis) > 0 ) : 
                all_values = list( parser.getValuesRecursively(yaml_di)  )
                # print(all_values)
                cnt += 1 
                prop_value = constants.YAML_SKIPPING_TEXT 
                if ( constants.DEPLOYMENT_KW in all_values ) : 
                    prop_value = constants.DEPLOYMENT_KW
                    lis.append( prop_value )
                elif ( constants.POD_KW in all_values ) :
                    prop_value = constants.POD_KW 
                    lis.append( prop_value )
                else: 
                    holder_ = [] 
                    parser.getValsFromKey(yaml_di, constants.KIND_KEY_NAME, holder_ )
                    if ( constants.K8S_SERVICE_KW in holder_ ): 
                        srv_val_li_ = [] 
                        parser.getValsFromKey( yaml_di, constants.K8S_APP_KW, srv_val_li_  ) 
                        for srv_val in srv_val_li_:
                            lis = graphtaint.mineServiceGraph( path_scrpt, yaml_di, srv_val )


            dic[ cnt ] = lis
    # print(dic) 
    return dic 


def scanForResourceLimits(path_scrpt):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_scrpt )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_scrpt )
        temp_ls = [] 
        parser.getKeyRecursively(yaml_di, temp_ls) 
        '''
        if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
        as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
        '''
        key_list = [ x_[0] for x_ in temp_ls  ]
        if ( (constants.CONTAINER_KW in key_list) and (constants.LIMITS_KW not in key_list ) and ( (constants.CPU_KW not in key_list)  or (constants.MEMORY_KW not in key_list) ) ):
            cnt += 1 
            if( len(temp_ls) > 0 ):
                all_values = list( parser.getValuesRecursively(yaml_di)  )
                # print(all_values)
                prop_value = constants.YAML_SKIPPING_TEXT 
                if ( constants.DEPLOYMENT_KW in all_values ) : 
                    prop_value = constants.DEPLOYMENT_KW
                    lis.append( prop_value )
                elif ( constants.POD_KW in all_values ) :
                    prop_value = constants.POD_KW 
                    lis.append( prop_value )
            dic[ cnt ] = lis
    # print(dic) 
    return dic 



def scanForRollingUpdates(path_script ):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_script )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_script )
        temp_ls = [] 
        parser.getKeyRecursively(yaml_di, temp_ls) 
        '''
        if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
        as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
        '''
        key_list = [ x_[0] for x_ in temp_ls  ]
        if ( (constants.STRATEGY_KW not in key_list ) and  (constants.ROLLING_UPDATE_KW not in key_list)   ):
            cnt += 1 
            if( len(temp_ls) > 0 ):
                all_values = list( parser.getValuesRecursively(yaml_di)  )
                # print(all_values)
                prop_value = constants.YAML_SKIPPING_TEXT 
                if ( constants.DEPLOYMENT_KW in all_values ) and ( constants.VAL_ROLLING_UPDATE_KW not in all_values ) : 
                    prop_value = constants.DEPLOYMENT_KW
                    lis.append( prop_value )
                elif ( constants.POD_KW in all_values ) and ( constants.VAL_ROLLING_UPDATE_KW not in all_values )  :
                    prop_value = constants.POD_KW 
                    lis.append( prop_value )
            dic[ cnt ] = lis
    # print(dic) 
    return dic     


def scanForMissingNetworkPolicy(path_script ):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_script )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_script )
        all_values = list( parser.getValuesRecursively(yaml_di)  )
        if ( constants.NET_POLICY_KW not in all_values ):
            cnt += 1 
            temp_ls = [] 
            parser.getKeyRecursively(yaml_di, temp_ls) 
            '''
            if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
            as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
            '''
            key_list = [ x_[0] for x_ in temp_ls  ]
            if ( (constants.SPEC_KW in key_list ) and  (constants.POD_SELECTOR_KW in key_list) and  (constants.MATCH_LABEL_KW in key_list) ):
                for src_val in all_values:
                    lis  = graphtaint.mineNetPolGraph(path_script, yaml_di, src_val, key_list )
            dic[ cnt ] = lis
    # print(dic) 
    return dic  

def scanForTruePID(path_script ):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_script )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_script )
        all_values = list( parser.getValuesRecursively(yaml_di)  )
        temp_ls = [] 
        parser.getKeyRecursively(yaml_di, temp_ls) 
        '''
        if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
        as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
        '''
        key_list = [ x_[0] for x_ in temp_ls  ]
        if (constants.SPEC_KW in key_list ) and ( constants.HOST_PID_KW in key_list ) :
            vals_for_pid = [] 
            parser.getValsFromKey(yaml_di, constants.HOST_PID_KW, vals_for_pid)
            # print(vals_for_pid)
            vals_for_pid = [str(z_) for z_ in vals_for_pid if isinstance( z_,  bool) ]
            vals_for_pid = [z_.lower() for z_ in vals_for_pid]
            if constants.TRUE_LOWER_KW in vals_for_pid: 
                cnt += 1 
                dic[ cnt ] = []
    return dic  


def scanForTrueIPC(path_script ):
    dic, lis   = {}, []
    if ( parser.checkIfValidK8SYaml( path_script )  ): 
        cnt = 0 
        yaml_di = parser.loadYAML( path_script )
        all_values = list( parser.getValuesRecursively(yaml_di)  )
        temp_ls = [] 
        parser.getKeyRecursively(yaml_di, temp_ls) 
        '''
        if you are using `parser.getKeyRecursively` to get all keys , you need to do some trnasformation to get the key names 
        as the output is a list of tuples so, `[(k1, v1), (k2, v2), (k3, v3)]`
        '''
        key_list = [ x_[0] for x_ in temp_ls  ]
        if (constants.SPEC_KW in key_list ) and ( constants.HOST_IPC_KW in key_list ) :
            vals_for_ipc = [] 
            parser.getValsFromKey(yaml_di, constants.HOST_IPC_KW, vals_for_ipc)
            vals_for_ipc = [str(z_) for z_ in vals_for_ipc if isinstance( z_,  bool) ]
            vals_for_ipc = [z_.lower() for z_ in vals_for_ipc]
            if constants.TRUE_LOWER_KW in vals_for_ipc: 
                cnt += 1 
                dic[ cnt ] = []
    return dic  


def runScanner(dir2scan):
    all_content   = [] 
    all_yml_files = getYAMLFiles(dir2scan)
    val_cnt       = 0 
    for yml_ in all_yml_files:
        '''
        Need to filter out `.github/workflows.yml files` first 
        '''
        if(parser.checkIfWeirdYAML ( yml_  )  == False): 
            if( parser.checkIfValidK8SYaml( yml_ ) ) or (  parser.checkIfValidHelm( yml_ ) ) :
                val_cnt = val_cnt + 1 
                print(constants.ANLYZING_KW + yml_ + constants.COUNT_PRINT_KW + str(val_cnt) )
                # get secrets and over privileges 
                within_secret_, templ_secret_, valid_taint_secr, valid_taint_privi  = scanSingleManifest( yml_ )
                # get insecure HTTP            
                http_dict             = scanForHTTP( yml_ )
                # get missing security context 
                absentSecuContextDict = scanForMissingSecurityContext( yml_ )
                # get use of default namespace 
                defaultNameSpaceDict  = scanForDefaultNamespace( yml_ )
                # get missing resource limit 
                absentResourceDict    = scanForResourceLimits( yml_ )
                # get absent rolling update count 
                rollingUpdateDict     = scanForRollingUpdates( yml_ )
                # get absent network policy count 
                absentNetPolicyDic    = scanForMissingNetworkPolicy( yml_ )
                all_content.append( ( dir2scan, yml_, within_secret_, templ_secret_, valid_taint_secr, valid_taint_privi, http_dict, absentSecuContextDict, defaultNameSpaceDict, absentResourceDict, rollingUpdateDict, absentNetPolicyDic ) )
                print(constants.SIMPLE_DASH_CHAR ) 


    return all_content



if __name__ == '__main__':
    # test_yaml = '/Users/arahman/K8S_REPOS/GITLAB_REPOS/kubernetes-tutorial-series-youtube/kubernetes-configuration-file-explained/nginx-deployment-result.yaml'
    # scanSingleManifest(test_yaml) 
    # another_yaml = '/Users/arahman/K8S_REPOS/GITLAB_REPOS/stackgres/stackgres-k8s/install/helm/stackgres-operator/values.yaml'
    # another_yaml = '/Users/arahman/K8S_REPOS/GITLAB_REPOS/justin@kubernetes/src/services/minecraft/values.yaml'

    # tp_yaml = '/Users/arahman/K8S_REPOS/GITLAB_REPOS/turkce-kubernetes/kubernetes-playground/replication-yontemlerine-genel-bakis/replication/deployment.yaml'
    # fp_yaml = 'TEST_ARTIFACTS/no.secu.nfs.yaml' 
    # scanForMissingSecurityContext( fp_yaml ) 

    # tp_http = '/Users/arahman/K8S_REPOS/GITLAB_REPOS/OpenStack-on-Kubernetes/src-ocata/configMap-glance-setup.yaml'
    # scanForHTTP( tp_http )

    tp_pid  = '/Users/arahman/K8S_REPOS/GITHUB_REPOS/kubernetes-ckad/01.kubernetes-in-action/Chapter13/pod-with-host-pid-and-ipc.yaml'
    pid_dic = scanForTrueIPC( tp_pid )
    print(pid_dic)