import yaml
import json
import hiyapyco
yaml = ruamel.yaml.YAML(typ='safe')
out_file = 'output.json'
def getYaml(path):
    with open(path, 'r') as yaml_in, open(out_file, "w") as json_out:
       
        yaml_object = yaml.safe_load(yaml_in) # yaml_object will be a list or a dict
        print(yaml_object)
        print(json.dump(yaml_object, json_out))


def mergeYaml(devPath,pymcPath='pymc.yaml'):
    #pymcYaml = getYaml('pymc.yaml')
    merged_yaml = hiyapyco.load(pymcPath,devPath, method=hiyapyco.METHOD_MERGE)
    
    f = open("tmp.yaml", "w")
    f.write(hiyapyco.dump(merged_yaml))
    f.close()

    return hiyapyco.dump(merged_yaml)
