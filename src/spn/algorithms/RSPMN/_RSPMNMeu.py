import logging

import numpy as np

import spn.algorithms.MEU as spmnMeu
from spn.algorithms.MEUTopDown import max_best_dec_with_meu
from spn.algorithms.MPE import get_node_funtions
from spn.algorithms.RSPMN.TemplateUtil import eval_template_top_down
from spn.structure.Base import Max
from spn.structure.Base import get_nodes_by_type
from spn.structure.leaves.spmnLeaves.SPMNLeaf import LatentInterface


def meu(self, template, data):
    """
    Evalautes bottom up by passing values of meu and likelihoods
    :return: meu at root node based on given observations
    """

    unrolled_network_meu_per_node = \
        self.eval_rspmn_bottom_up_for_meu(template, data)[0]
    # ll at root node
    meu = unrolled_network_meu_per_node[-1][:, 0]

    # print(f'unrolled_network_meu_per_node {unrolled_network_meu_per_node}')
    return meu


def value_iteration(self, template, iterations):

    num_variables_each_time_step = len(self.params.feature_names)

    data = [np.nan]*(num_variables_each_time_step*iterations)
    data = np.array(data).reshape(1, -1)

    unrolled_network_meu_per_node, unrolled_network_likelihood_per_node = \
        self.eval_rspmn_bottom_up_for_meu(template, data)

    return unrolled_network_meu_per_node, unrolled_network_likelihood_per_node


def eval_rspmn_bottom_up_for_meu(self, template, data):
    """
    :return: unrolled_network_meu_per_node, unrolled_network_likelihood_per_node
    list of meus/likelihoods of networks corresponding to each time step
    starting with bottom most to top network.
    Note: stores dummy bottom + 1 time step meu/likelihoods
    as 0th element in list
    """
    # assert self.InitialTemplate.top_network is not None,
    # f'top layer does not exist'
    # assert self.template is not None, f'template layer does not exist'

    assert type(data) is np.ndarray, 'data should be of type numpy array'

    num_variables_each_time_step, total_num_of_time_steps, \
        initial_num_latent_interface_nodes = \
        self.get_params_for_get_each_time_step_data_for_template(template,
                                                                 data)

    logging.debug(
        f'intial_num_latent_interface_nodes '
        f'{initial_num_latent_interface_nodes}')
    logging.debug(f'total_num_of_time_steps {total_num_of_time_steps}')

    template_nodes = get_nodes_by_type(template)
    latent_interface_list = []
    for node in template_nodes:
        if type(node) == LatentInterface:
            latent_interface_list.append(node)


    # for bottom most time step + 1
    likelihood_per_node = np.zeros((data.shape[0], len(template_nodes)))
    unrolled_network_likelihood_per_node = [likelihood_per_node]

    meu_per_node = np.zeros((data.shape[0], len(template_nodes)))
    unrolled_network_meu_per_node = [meu_per_node]

    # evaluate template bottom up at each time step
    for time_step_num_in_reverse_order in range(total_num_of_time_steps - 1,
                                                -1, -1):

        logging.debug(
            f'time_step_num_in_reverse_order '
            f'{time_step_num_in_reverse_order}')

        prev_likelihood_per_node = unrolled_network_likelihood_per_node[-1]
        logging.debug(f'prev_likelihood_per_node {prev_likelihood_per_node.shape}')
        print(f'prev_likelihood_per_node {prev_likelihood_per_node}')

        prev_meu_per_node = unrolled_network_meu_per_node[-1]
        logging.debug(f'prev_meu_per_node {prev_meu_per_node.shape}')
        print(f'prev_meu_per_node {prev_meu_per_node}')

        # attach likelihoods of bottom interface root nodes as
        # data for latent leaf vars
        each_time_step_data_for_template = \
            self.get_each_time_step_data_for_meu(
                data,
                time_step_num_in_reverse_order,
                total_num_of_time_steps,
                prev_likelihood_per_node,
                initial_num_latent_interface_nodes,
                num_variables_each_time_step,
                bottom_up=True
            )
        # if time step is 0, evaluate top network
        if time_step_num_in_reverse_order == 0:

            print(
                f'each_time_step_data_for_template: {each_time_step_data_for_template}')

            top_nodes = get_nodes_by_type(self.InitialTemplate.top_network)
            meu_per_node = np.zeros((data.shape[0], len(top_nodes)))
            meu_per_node.fill(np.nan)
            likelihood_per_node = np.zeros((data.shape[0], len(top_nodes)))

            top_latent_interface_list = []
            for node in top_nodes:
                if type(node) == LatentInterface:
                    top_latent_interface_list.append(node)

            # replace values of latent leaf nodes with
            # bottom time step meu values
            self.pass_meu_val_to_latent_interface_leaf_nodes(
                meu_per_node, prev_meu_per_node,
                initial_num_latent_interface_nodes, top_latent_interface_list)

            print(f'initial meu_per_node {meu_per_node}')

            spmnMeu.meu(self.InitialTemplate.top_network,
                        each_time_step_data_for_template,
                        meu_matrix=meu_per_node,
                        lls_matrix=likelihood_per_node
                                     )

            # eval_val_per_node = meu_matrix
            #print(f'meu_per_node {meu_per_node}')
            # print(f'likelihood_per_node {likelihood_per_node}')
            # print(f'meu_matrix {meu_matrix}')

        else:
            meu_per_node = np.zeros((data.shape[0], len(template_nodes)))
            meu_per_node.fill(np.nan)
            likelihood_per_node = np.zeros((data.shape[0], len(template_nodes)))

            # replace values of latent leaf nodes with
            # bottom time step meu values
            self.pass_meu_val_to_latent_interface_leaf_nodes(
                meu_per_node, prev_meu_per_node,
                initial_num_latent_interface_nodes, latent_interface_list)
            print(f'initial meu_per_node {meu_per_node}')
            spmnMeu.meu(template,
                        each_time_step_data_for_template,
                        meu_matrix=meu_per_node,
                        lls_matrix=likelihood_per_node
                                     )

            # meu_per_node = meu_matrix
            #print(f'meu_per_node {meu_per_node}')
            # print(f'likelihood_per_node {likelihood_per_node}')

        unrolled_network_likelihood_per_node.append(likelihood_per_node)
        unrolled_network_meu_per_node.append(meu_per_node)

    # print(unrolled_network_meu_per_node[-1][:, 0])

    return unrolled_network_meu_per_node, unrolled_network_likelihood_per_node


def topdowntraversal_and_bestdecisions(self, template, data):
    """
    :param data: data for n number of time steps
    :return: Fills nan values with mpe for leaf nodes based on likelihood
    and best decisions for max nodes based on meu
    """

    node_functions = get_node_funtions()
    node_functions_top_down = node_functions[0].copy()
    node_functions_top_down.update({Max: max_best_dec_with_meu})
    # node_functions_bottom_up = node_functions[2].copy()
    # logging.debug(f'_node_functions_bottom_up {node_functions_bottom_up}')


    # one pass bottom up evaluating the likelihoods
    # unrolled_network_lls_per_node = self.log_likelihood(template, data)[1]

    # one pass bottom up for meu and likelihood
    unrolled_network_meu_per_node, unrolled_network_lls_per_node = \
        self.eval_rspmn_bottom_up_for_meu(template, data, False)

    num_variables_each_time_step, total_num_of_time_steps, \
        initial_num_latent_interface_nodes = \
        self.get_params_for_get_each_time_step_data_for_template(template,
                                                                 data)
    # top down traversal
    for time_step_num in range(total_num_of_time_steps):
        lls_per_node = unrolled_network_lls_per_node[
            total_num_of_time_steps - time_step_num
            ]
        meu_per_node = unrolled_network_meu_per_node[
            total_num_of_time_steps - time_step_num
            ]

        each_time_step_data_for_template = \
            self.get_each_time_step_data_for_template(
                data, time_step_num,
                total_num_of_time_steps,
                lls_per_node,
                initial_num_latent_interface_nodes,
                num_variables_each_time_step,
                bottom_up=False
            )

        instance_ids = np.arange(each_time_step_data_for_template.shape[0])
        # if time step is 0, evaluate top network
        if time_step_num == 0:
            all_results, latent_interface_dict = eval_template_top_down(
                self.InitialTemplate.top_network,
                node_functions_top_down, False,
                all_results=None, parent_result=instance_ids,
                meu_per_node=meu_per_node,
                data=each_time_step_data_for_template,
                lls_per_node=lls_per_node)

        else:

            all_results, latent_interface_dict = eval_template_top_down(
                template,
                node_functions_top_down, False,
                all_results=None, parent_result=instance_ids,
                meu_per_node=meu_per_node,
                data=each_time_step_data_for_template,
                lls_per_node=lls_per_node
            )
        # initialise template.interface_winner.
        # Each instance must reach one leaf interface node.
        # Initial interface node number is infinite
        template.interface_winner = np.full(
            (each_time_step_data_for_template.shape[0],), np.inf
        )
        logging.debug(f'latent_interface_dict {latent_interface_dict}')
        # for each instance assign the interface node reached
        for latent_interface_node, instances in \
                latent_interface_dict.items():
            template.interface_winner[instances] = \
                latent_interface_node.interface_idx - \
                num_variables_each_time_step

        # fill data with values returned by filling each time step data through
        # top down traversal
        data[
            :,
            (time_step_num * num_variables_each_time_step):
            (time_step_num * num_variables_each_time_step) +
            num_variables_each_time_step
        ] = \
            each_time_step_data_for_template[:, 0:num_variables_each_time_step]

        # print(data)

    return data


def select_actions(self, template, data,
                   unrolled_network_meu_per_node,
                   unrolled_network_lls_per_node):

    node_functions = get_node_funtions()
    node_functions_top_down = node_functions[0].copy()
    node_functions_top_down.update({Max: max_best_dec_with_meu})
    # node_functions_bottom_up = node_functions[2].copy()
    # logging.debug(f'_node_functions_bottom_up {node_functions_bottom_up}')

    # one pass bottom up evaluating the likelihoods
    # unrolled_network_lls_per_node = self.log_likelihood(template, data)[1]

    # one pass bottom up for meu and likelihood
    # unrolled_network_meu_per_node, unrolled_network_lls_per_node = \
    #     self.eval_rspmn_bottom_up_for_meu(template, data, False)
    # num_variables_each_time_step = len(self.params.feature_names)
    # total_num_of_time_steps = int(
    #     data.shape[1] / num_variables_each_time_step)
    num_variables_each_time_step, total_num_of_time_steps, \
        initial_num_latent_interface_nodes = \
        self.get_params_for_get_each_time_step_data_for_template(template,
                                                                 data)
    # top down traversal. Executes only for one time step as data is only for
    # single time step
    for time_step_num in range(total_num_of_time_steps):
        lls_per_node = unrolled_network_lls_per_node[
            total_num_of_time_steps - time_step_num
            ]
        meu_per_node = unrolled_network_meu_per_node[
            total_num_of_time_steps - time_step_num
            ]

        each_time_step_data_for_template = \
            self.get_each_time_step_data_for_template(
                data, time_step_num,
                total_num_of_time_steps,
                lls_per_node,
                initial_num_latent_interface_nodes,
                num_variables_each_time_step,
                bottom_up=False
            )

        instance_ids = np.arange(each_time_step_data_for_template.shape[0])
        # if time step is 0, evaluate top network
        if time_step_num == 0:
            eval_template_top_down(
                self.InitialTemplate.top_network,
                node_functions_top_down, False,
                all_results=None, parent_result=instance_ids,
                meu_per_node=meu_per_node,
                data=each_time_step_data_for_template,
                lls_per_node=lls_per_node)

        # else:
        #
        #     all_results, latent_interface_dict = eval_template_top_down(
        #         template,
        #         node_functions_top_down, False,
        #         all_results=None, parent_result=instance_ids,
        #         meu_per_node=meu_per_node,
        #         data=each_time_step_data_for_template,
        #         lls_per_node=lls_per_node
        #     )
        # # initialise template.interface_winner.
        # # Each instance must reach one leaf interface node.
        # # Initial interface node number is infinite
        # template.interface_winner = np.full(
        #     (each_time_step_data_for_template.shape[0],), np.inf
        # )
        # logging.debug(f'latent_interface_dict {latent_interface_dict}')
        # # for each instance assign the interface node reached
        # for latent_interface_node, instances in \
        #         latent_interface_dict.items():
        #     template.interface_winner[instances] = \
        #         latent_interface_node.interface_idx - \
        #         num_variables_each_time_step

        # fill data with values returned by filling each time step data through
        # top down traversal
        data[
            :,
            (time_step_num * num_variables_each_time_step):
            (time_step_num * num_variables_each_time_step) +
            num_variables_each_time_step
            ] = \
            each_time_step_data_for_template[:, 0:num_variables_each_time_step]

        # print(data)

    return data


def meu_of_state(self, template, data,
                 unrolled_network_meu_per_node,
                 unrolled_network_likelihood_per_node):
    assert type(data) is np.ndarray, 'data should be of type numpy array'

    num_variables_each_time_step, total_num_of_time_steps, \
    initial_num_latent_interface_nodes = \
        self.get_params_for_get_each_time_step_data_for_template(template,
                                                                 data)

    logging.debug(
        f'intial_num_latent_interface_nodes '
        f'{initial_num_latent_interface_nodes}')
    logging.debug(f'total_num_of_time_steps {total_num_of_time_steps}')

    template_nodes = get_nodes_by_type(template)
    latent_interface_list = []
    for node in template_nodes:
        if type(node) == LatentInterface:
            latent_interface_list.append(node)

    # # for bottom most time step + 1
    # likelihood_per_node = np.zeros((data.shape[0], len(template_nodes)))
    # unrolled_network_likelihood_per_node = [likelihood_per_node]
    #
    # meu_per_node = np.zeros((data.shape[0], len(template_nodes)))
    # unrolled_network_meu_per_node = [meu_per_node]

    # evaluate template bottom up at each time step
    for time_step_num_in_reverse_order in range(total_num_of_time_steps - 1,
                                                -1, -1):

        logging.debug(
            f'time_step_num_in_reverse_order '
            f'{time_step_num_in_reverse_order}')

        prev_likelihood_per_node = unrolled_network_likelihood_per_node[-2]
        logging.debug(
            f'prev_likelihood_per_node {prev_likelihood_per_node.shape}')
        print(f'prev_likelihood_per_node {prev_likelihood_per_node}')

        prev_meu_per_node = unrolled_network_meu_per_node[-2]
        logging.debug(f'prev_meu_per_node {prev_meu_per_node.shape}')
        print(f'prev_meu_per_node {prev_meu_per_node}')

        # attach likelihoods of bottom interface root nodes as
        # data for latent leaf vars
        each_time_step_data_for_template = \
            self.get_each_time_step_data_for_meu(
                data,
                time_step_num_in_reverse_order,
                total_num_of_time_steps,
                prev_likelihood_per_node,
                initial_num_latent_interface_nodes,
                num_variables_each_time_step,
                bottom_up=True
            )
        # if time step is 0, evaluate top network
        if time_step_num_in_reverse_order == 0:

            print(
                f'each_time_step_data_for_template: {each_time_step_data_for_template}')

            top_nodes = get_nodes_by_type(self.InitialTemplate.top_network)
            meu_per_node = np.zeros((data.shape[0], len(top_nodes)))
            meu_per_node.fill(np.nan)
            likelihood_per_node = np.zeros((data.shape[0], len(top_nodes)))

            top_latent_interface_list = []
            for node in top_nodes:
                if type(node) == LatentInterface:
                    top_latent_interface_list.append(node)

            # replace values of latent leaf nodes with
            # bottom time step meu values
            self.pass_meu_val_to_latent_interface_leaf_nodes(
                meu_per_node, prev_meu_per_node,
                initial_num_latent_interface_nodes, top_latent_interface_list)

            print(f'initial meu_per_node {meu_per_node}')

            spmnMeu.meu(self.InitialTemplate.top_network,
                        each_time_step_data_for_template,
                        meu_matrix=meu_per_node,
                        lls_matrix=likelihood_per_node
                        )

            # eval_val_per_node = meu_matrix
            # print(f'meu_per_node {meu_per_node}')
            # print(f'likelihood_per_node {likelihood_per_node}')
            # print(f'meu_matrix {meu_matrix}')

        else:
            meu_per_node = np.zeros((data.shape[0], len(template_nodes)))
            meu_per_node.fill(np.nan)
            likelihood_per_node = np.zeros((data.shape[0], len(template_nodes)))

            # replace values of latent leaf nodes with
            # bottom time step meu values
            self.pass_meu_val_to_latent_interface_leaf_nodes(
                meu_per_node, prev_meu_per_node,
                initial_num_latent_interface_nodes, latent_interface_list)
            print(f'initial meu_per_node {meu_per_node}')
            spmnMeu.meu(template,
                        each_time_step_data_for_template,
                        meu_matrix=meu_per_node,
                        lls_matrix=likelihood_per_node
                        )

            # meu_per_node = meu_matrix
            # print(f'meu_per_node {meu_per_node}')
            # print(f'likelihood_per_node {likelihood_per_node}')

        # unrolled_network_likelihood_per_node.append(likelihood_per_node)
        # unrolled_network_meu_per_node.append(meu_per_node)

    # print(unrolled_network_meu_per_node[-1][:, 0])

    #return unrolled_network_meu_per_node, unrolled_network_likelihood_per_node

    return meu_per_node[:, 0]
