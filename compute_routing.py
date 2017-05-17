import math

from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from datatools import list_companies, insert_result, get_distance_matrix
import logging
import googlemaps
import urllib.request, json

correspondance_case_identreprise = []


class CreateDistanceCallback(object):
    """Create callback to calculate distances between points."""

    def __init__(self, locations):
        """Initialize distance array."""

        self.matrix = get_distance_matrix()

    def distance_osrm(self, locations):
        weburl = "http://router.project-osrm.org/table/v1/driving/"
        for l in locations:
            weburl = weburl + str(l[0]) + "," + str(l[1]) + ";"

        # je retire le dernier ; ajoute a la fin
        weburl = weburl[:-1]
        with urllib.request.urlopen(weburl) as url:
            data = json.loads(url.read().decode())
            self.matrix = data["durations"]

    def distance_google(self, locations):

        # origins = list(locations)
        # destinations = list(locations)

        client = googlemaps.Client("AIzaSyD0hkj4gC-MwkLwLx0dgvjt4XKuI-tk_bg")

        # matrix = client.distance_matrix(origins, destinations)

        num_locations = len(locations)
        self.matrix = {}

        for from_node in range(num_locations):
            self.matrix[from_node] = {}
            for to_node in range(num_locations):
                if from_node == to_node:
                    self.matrix[from_node][to_node] = 0
                else:
                    p1 = locations[from_node]
                    p2 = locations[to_node]

                    print(from_node, to_node)

                    self.matrix[from_node][to_node] = client.distance_matrix([p1], [p2])

    def Distance(self, from_node, to_node):

        dep=correspondance_case_identreprise[from_node]
        arr=correspondance_case_identreprise[to_node]

        #petit hack, le depot est toujours a une distance de 0
        if dep == 66 or arr ==66:
            return 0

        return self.matrix[dep][arr]



# Demand callback
class CreateDemandCallback(object):
    """Create callback to get demands at each location."""

    def __init__(self, demands):
        self.matrix = demands

    def Demand(self, from_node, to_node):
        return self.matrix[from_node]


def main():
    logging.basicConfig(level=logging.INFO)

    # Create the data.
    locations, demands = create_data_array()

    num_locations = len(locations)
    depot = 0  # The depot is the start and end point of each route.
    num_vehicles = math.ceil((num_locations - 1) / 5)

    # Create routing model.
    if num_locations > 0:

        logging.info("Calcul des meilleurs trajets avec %s sites et %s visiteurs", num_locations, num_vehicles)

        routing = pywrapcp.RoutingModel(num_locations, num_vehicles, depot)
        search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()

        # Setting first solution heuristic: the
        # method for finding a first solution to the problem.
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

        # The 'PATH_CHEAPEST_ARC' method does the following:
        # Starting from a route "start" node, connect it to the node which produces the
        # cheapest route segment, then extend the route by iterating on the last
        # node added to the route.

        # Put a callback to the distance function here. The callback takes two
        # arguments (the from and to node indices) and returns the distance between
        # these nodes.

        dist_between_locations = CreateDistanceCallback(locations)
        dist_callback = dist_between_locations.Distance
        routing.SetArcCostEvaluatorOfAllVehicles(dist_callback)

        # Put a callback to the demands.
        demands_at_locations = CreateDemandCallback(demands)
        demands_callback = demands_at_locations.Demand

        # Add a dimension for demand.
        slack_max = 0
        vehicle_capacity = 5
        fix_start_cumul_to_zero = True
        demand = "Demand"
        routing.AddDimension(demands_callback, slack_max, vehicle_capacity,
                             fix_start_cumul_to_zero, demand)

        # Solve, displays a solution if any.
        assignment = routing.SolveWithParameters(search_parameters)
        if assignment:
            # Display solution.
            # Solution cost.
            print("Total distance of all routes: " + str(assignment.ObjectiveValue()) )

            result_by_vehicule = []

            for vehicle_nbr in range(num_vehicles):
                index = routing.Start(vehicle_nbr)
                index_next = assignment.Value(routing.NextVar(index))
                route = ''
                route_dist = 0
                route_demand = 0

                while not routing.IsEnd(index_next):

                    node_index = routing.IndexToNode(index)
                    node_index_next = routing.IndexToNode(index_next)

                    if node_index != depot:
                        route += str(correspondance_case_identreprise[node_index]) + " -> "

                    # Add the distance to the next node.
                    route_dist += dist_callback(node_index, node_index_next)
                    # Add demand.
                    route_demand += demands[node_index_next]
                    index = index_next
                    index_next = assignment.Value(routing.NextVar(index))

                node_index = routing.IndexToNode(index)
                node_index_next = routing.IndexToNode(index_next)
                route += str(correspondance_case_identreprise[node_index])
                route_dist += dist_callback(node_index, node_index_next)

                print("\nVehicle " + str(vehicle_nbr) )
                print("\tRoute : " + route)
                print("\tDistance of route : " + str(route_dist))
                print("\tDemand met : " + str(route_demand) )

                result_by_vehicule.append((vehicle_nbr, route, route_dist, route_demand))

            insert_result(assignment.ObjectiveValue(), num_locations, num_vehicles, result_by_vehicule)

        else:
            print('No solution found.')
    else:
        print('Specify an instance greater than 0.')


def create_data_array():

    locations = []

    logging.info("recuperation des entreprises")


    for row in list_companies():

        # a la case i on trouve l'entreprise n° x
        correspondance_case_identreprise.append(row[0])

        # locations.append((row[4], row[5]))

        nom = row[1]
        cp = row[2]
        ville = row[3]

        adresse = nom + ", " + cp + ", " + ville + ", France "
        locations.append(adresse)

    demands = [1] * len(locations)
    demands[0] = 0

    return locations, demands


if __name__ == '__main__':
    main()
