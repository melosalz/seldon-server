import pprint
import argparse
import sys
import os
import json
import errno

import zk_utils

gdata = {
    'all_clients_node_path': "/all_clients",
}

def pp(o):
    p = pprint.PrettyPrinter(indent=4)
    p.pprint(o)

def getOpts(args):
    parser = argparse.ArgumentParser(prog='seldon-cli client', description='Seldon Cli')
    parser.add_argument('--action', help="the action to use", required=True)
    parser.add_argument('--client-name', help="the name of the client", required=False)
    parser.add_argument('--recommender-name', help="the name of recommender", required=False)
    parser.add_argument('args', nargs=argparse.REMAINDER) # catch rest (non-options) as args
    opts = parser.parse_args(args)
    return opts

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def dict_to_json(d, expand=False):
    return json.dumps(d, sort_keys=True, indent=4, separators=(',', ': ')) if expand else json.dumps(d, sort_keys=True, separators=(',',':'))

def json_to_dict(json_data):
    return json.loads(json_data)

def write_data_to_file(data_fpath, data):
    json = dict_to_json(data, True) if isinstance(data,dict) else str(data)
    mkdir_p(os.path.dirname(data_fpath))
    f = open(data_fpath,'w')
    f.write(json)
    f.write('\n')
    f.close()
    print "Writing data to file[{data_fpath}]".format(**locals())

def write_node_value_to_file(zk_client, zkroot, node_path):
    node_value = zk_utils.node_get(zk_client, node_path)
    node_value = node_value.strip()
    if zk_utils.is_json_data(node_value):
        data = json_to_dict(node_value) if node_value != None and len(node_value)>0 else ""
    else:
        data = str(node_value)
    data_fpath = zkroot + node_path + "/_data_"
    write_data_to_file(data_fpath, data)


def is_existing_client(zkroot, client_name):
    client_names = os.listdir(zkroot + gdata["all_clients_node_path"])
    if client_name in client_names:
        return True
    else:
        return False

def show_algs(data):
    combiner = data["combiner"]
    algorithms = data["algorithms"]
    print "algorithms:"
    for alg in algorithms:
        print "    {alg_name}".format(alg_name=alg["name"])
        for config_item in alg["config"]:
            print "        {n}={v}".format(n=config_item["name"],v=config_item["value"])
    print "combiner: "+combiner

def ensure_client_has_algs(zkroot, zk_client, client_name):
    data_fpath = "{zkroot}{all_clients_node_path}/{client_name}/algs/_data_".format(zkroot=zkroot,all_clients_node_path=gdata["all_clients_node_path"],client_name=client_name)
    if not os.path.isfile(data_fpath):
        node_path = gdata["all_clients_node_path"]+"/"+client_name+"/algs"
        if zk_client.exists(node_path):
            write_node_value_to_file(zk_client, zkroot, node_path)
        else:
            default_alg_json = '{"algorithms":[{"config":[],"filters":[],"includers":[],"name":"recentItemsRecommender"}],"combiner":"firstSuccessfulCombiner"}'
            data = json_to_dict(default_alg_json)
            write_data_to_file(data_fpath, data)
            zk_utils.node_set(zk_client, node_path, dict_to_json(data))

def action_show(command_data, opts):
    client_name = opts.client_name
    if client_name == None:
        print "Need client name to show the algs for"
        sys.exit(1)

    zkroot = command_data["zkdetails"]["zkroot"]
    if not is_existing_client(zkroot, client_name):
        print "Invalid client[{client_name}]".format(**locals())
        sys.exit(1)

    zk_client = command_data["zkdetails"]["zk_client"]
    ensure_client_has_algs(zkroot, zk_client, client_name)

    data_fpath = zkroot + gdata["all_clients_node_path"] + "/" + client_name + "/algs/_data_"
    f = open(data_fpath)
    json = f.read()
    f.close()
    data = json_to_dict(json)
    show_algs(data)

def action_add(command_data, opts):
    client_name = opts.client_name
    if client_name == None:
        print "Need client name to add algs for"
        sys.exit(1)

    recommender_name = opts.recommender_name
    if recommender_name == None:
        print "Need recommender name"
        sys.exit(1)

    zkroot = command_data["zkdetails"]["zkroot"]
    if not is_existing_client(zkroot, client_name):
        print "Invalid client[{client_name}]".format(**locals())
        sys.exit(1)

    default_algorithms = command_data["conf_data"]["default_algorithms"]
    recommenders = default_algorithms.keys()

    if recommender_name not in recommenders:
        print "Invalid recommender[{recommender_name}]".format(**locals())
        sys.exit(1)

    zk_client = command_data["zkdetails"]["zk_client"]
    ensure_client_has_algs(zkroot, zk_client, client_name)

    data_fpath = zkroot + gdata["all_clients_node_path"] + "/" + client_name + "/algs/_data_"
    f = open(data_fpath)
    json = f.read()
    f.close()
    data = json_to_dict(json)

    algorithms = data["algorithms"]
    includers = default_algorithms[recommender_name]["includers"] if default_algorithms[recommender_name].has_key("includers") else []
    recommender_data = {
            'filters':[],
            'includers': includers,
            'name': recommender_name,
            'config': default_algorithms[recommender_name]["config"]
    }
    algorithms.append(recommender_data)
    write_data_to_file(data_fpath, data)
    print "Added [{recommender_name}]".format(**locals())
    show_algs(data)

def action_delete(command_data, opts):
    client_name = opts.client_name
    if client_name == None:
        print "Need client name to add algs for"
        sys.exit(1)

    recommender_name = opts.recommender_name
    if recommender_name == None:
        print "Need recommender name"
        sys.exit(1)

    zkroot = command_data["zkdetails"]["zkroot"]
    if not is_existing_client(zkroot, client_name):
        print "Invalid client[{client_name}]".format(**locals())
        sys.exit(1)

    zk_client = command_data["zkdetails"]["zk_client"]
    ensure_client_has_algs(zkroot, zk_client, client_name)

    data_fpath = zkroot + gdata["all_clients_node_path"] + "/" + client_name + "/algs/_data_"
    f = open(data_fpath)
    json = f.read()
    f.close()
    data = json_to_dict(json)

    default_algorithms = command_data["conf_data"]["default_algorithms"]
    recommenders = default_algorithms.keys()

    if recommender_name not in recommenders:
        print "Invalid recommender[{recommender_name}]".format(**locals())
        sys.exit(1)

    algorithms = data["algorithms"]

    length_before_removal = len(algorithms)
    def recommender_filter(item):
        if item["name"] == recommender_name:
            return False
        else:
            return True
    filtered_algorithms = filter(recommender_filter, algorithms)
    length_after_removal = len(filtered_algorithms)
    data["algorithms"] = filtered_algorithms
    if length_after_removal < length_before_removal:
        write_data_to_file(data_fpath, data)
        print "Removed [{recommender_name}]".format(**locals())

def action_list(command_data, opts):
    print "Default recommenders:"
    default_algorithms = command_data["conf_data"]["default_algorithms"]
    for recommender in default_algorithms:
        print "    {recommender}".format(**locals())

def action_commit(command_data, opts):
    client_name = opts.client_name
    if client_name == None:
        print "Need client name to add algs for"
        sys.exit(1)

    zkroot = command_data["zkdetails"]["zkroot"]
    if not is_existing_client(zkroot, client_name):
        print "Invalid client[{client_name}]".format(**locals())
        return

    zk_client = command_data["zkdetails"]["zk_client"]
    zkroot = command_data["zkdetails"]["zkroot"]
    data_fpath = zkroot + gdata["all_clients_node_path"] + "/" + client_name + "/algs/_data_"
    if not os.path.isfile(data_fpath):
        "Data to commit not found!!"
    f = open(data_fpath)
    data_json = f.read()
    f.close()

    zk_client = command_data["zkdetails"]["zk_client"]
    node_path = gdata["all_clients_node_path"] + "/" + client_name + "/algs"
    zk_utils.node_set(zk_client, node_path, data_json)

def cmd_alg(command_data, command_args):
    actions = {
        "list" : action_list,
        "show" : action_show,
        "add" : action_add,
        "delete" : action_delete,
        "commit" : action_commit,
    }

    opts = getOpts(command_args)

    action = opts.action
    if action == None:
        actions["default"](command_data, opts)
    else:
        if actions.has_key(action):
            actions[action](command_data, opts)
        else:
            print "Invalid action[{}]".format(action)