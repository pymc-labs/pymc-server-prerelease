import yaml
import json
import hiyapyco


def mergeYaml(devPath,pymcPath='pymc.yaml'):
    #pymcYaml = getYaml('pymc.yaml')
    merged_yaml = hiyapyco.load(pymcPath,devPath, method=hiyapyco.METHOD_MERGE)
    
    f = open("tmp.yaml", "w")
    f.write(hiyapyco.dump(merged_yaml))
    f.close()

    return hiyapyco.dump(merged_yaml)
