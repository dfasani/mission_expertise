#!/usr/bin/python
import geocoder
import sqlite3
import logging
import googlemaps
import pprint


def compute_distances_between_companies():
    correspondance_case_identreprise = []

    locations = []

    for row in list_companies():
        # if (len(locations) > 5):
        #    break;

        # a la case i on trouve l'entreprise n° x
        correspondance_case_identreprise.append(row[0])

        # locations.append((row[4], row[5]))

        nom = row[1]
        cp = row[2]
        ville = row[3]

        adresse = nom + ", " + cp + ", " + ville + ", France "
        locations.append(adresse)

    matrix = {}

    client = googlemaps.Client("AIzaSyD0hkj4gC-MwkLwLx0dgvjt4XKuI-tk_bg")

    num_locations = len(locations)

    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    for from_node in range(num_locations):
        matrix[from_node] = {}
        for to_node in range(num_locations):
            if from_node == to_node:
                matrix[from_node][to_node] = 0
            else:
                p1 = locations[from_node]
                p2 = locations[to_node]

                distance_matrix = client.distance_matrix([p1], [p2], mode="driving")

                print(from_node, to_node, distance_matrix)

                # print("a",distance_matrix["rows"])
                # print("b",distance_matrix["rows"][0])
                # print("c",distance_matrix["rows"][0]["elements"])
                # print("d",distance_matrix["rows"][0]["elements"][0]["distance"])
                # print("e",distance_matrix["rows"][0]["elements"][0]["distance"]["value"])

                distance = int(distance_matrix["rows"][0]["elements"][0]["distance"]["value"])
                matrix[from_node][to_node] = distance

                cursor.execute("INSERT INTO distance_entreprise VALUES ('%s','%s','%s')" % (
                    correspondance_case_identreprise[from_node], correspondance_case_identreprise[to_node], distance))

    conn.commit()
    conn.close()


def update_companies_latlng():
    logging.info("maj des coordonnées GPS des entreprises...")

    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    for row in cursor.execute('SELECT * FROM entreprise WHERE lat IS NULL'):

        nom = row[1]
        cp = row[2]
        ville = row[3]

        adresse = nom + ", " + cp + ", " + ville + ", France "

        coordonnees = geocoder.google(adresse).latlng

        print(row, coordonnees)

        # le geocoding ne fonctionne pas parfois, on laisse qques chances
        if len(coordonnees) == 0:
            for _ in range(2):
                if len(coordonnees) == 0:
                    # sleep(randint(1,3))
                    coordonnees = geocoder.google(adresse).latlng

        if len(coordonnees) == 0:
            raise ValueError("adresse introuvable", adresse)

        sqlUpdate = 'UPDATE entreprise  SET lat={} , lng={} WHERE id={}'.format(coordonnees[0], coordonnees[1], row[0])
        conn.cursor().execute(sqlUpdate)

        conn.commit()

    # disconnect from server
    conn.close()

    logging.info("maj des coordonnées GPS des entreprises   [OK]")


def get_distance_matrix():
    matrix = {}

    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    for row in cursor.execute('SELECT * FROM distance_entreprise order by id_entreprise_depart, id_entreprise_arrivee'):
        id_dep = row[0]
        id_arr = row[1]
        dist = row[2]

        if not id_dep in matrix:
            matrix[id_dep] = {}
            matrix[id_dep][id_dep] = 0

        matrix[id_dep][id_arr] = int(dist)

    # disconnect from server
    conn.close()

    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(matrix)

    return matrix


def list_companies():
    results = []

    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    for row in cursor.execute('SELECT * FROM entreprise ORDER BY nom'):
        results.append(row)

    # disconnect from server
    conn.close()

    return results


def list_demand_by_locations():
    results = []

    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    sql = '''
        select entreprise.id, entreprise.nom, entreprise.cp, entreprise.ville, count(*) as nb_eleves
        from eleve, entreprise
        where eleve.id_entreprise = entreprise.id
        group by entreprise.nom, entreprise.cp, entreprise.ville
        order by entreprise.nom, entreprise.cp, entreprise.ville
    '''

    for row in cursor.execute(sql):
        results.append(row)

    # disconnect from server
    conn.close()

    return results


def list_students():
    results = []

    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    for row in cursor.execute('SELECT * FROM eleve ORDER BY nom'):
        results.append(row)

    # disconnect from server
    conn.close()

    return results


def insert_result(distanceTotale, num_locations, num_vehicles, result_by_vehicule):
    # Open database connection
    conn = sqlite3.connect('missionexpertise.db')

    # prepare a cursor object using cursor() method
    cursor = conn.cursor()

    cursor.execute("INSERT INTO calcul(distance_totale,nb_sites,nb_visiteurs) VALUES ('%s','%s','%s')" % (
        distanceTotale, num_locations, num_vehicles))

    idcalcul = cursor.lastrowid

    for result in result_by_vehicule:
        vehicle_nbr, route, route_dist, route_demand = result
        cursor.execute(
            "INSERT INTO distance(id_calcul,num_vehicule,distance,nb_etapes) VALUES ('%s','%s','%s','%s')" % (
                idcalcul, vehicle_nbr, route_dist, route_demand))

        etapes = route.split(" -> ")

        for i, etape in enumerate(etapes):
            etape = int(etape)
            cursor.execute(
                "INSERT INTO etape(id_calcul,num_vehicule,id_entreprise,ordre) VALUES ('%s','%s','%s','%d')" % (
                    idcalcul, vehicle_nbr, etape, i))

    # enregistre les changements
    conn.commit()

    # disconnect from server
    conn.close()


if __name__ == '__main__':

    # compute_distances_between_companies()
    get_distance_matrix()

    print()
    print("-- entreprises --")
    print()

    for row in list_companies():
        nom = row[1]
        cp = row[2]
        ville = row[3]

        # Now print fetched result
        print("nom=%s,cp=%s,ville=%s" % (nom, cp, ville))

    print()
    print("-- etudiants --")
    print()

    for row in list_students():
        nom = row[1]
        prenom = row[2]

        # Now print fetched result
        print("nom=%s,prenom=%s" % (nom, prenom))

    print()
    print("-- entreprises --")
    print()

    for row in list_demand_by_locations():
        nom = row[1]
        cp = row[2]
        ville = row[3]
        demande = row[4]

        # Now print fetched result
        print("nom=%s,cp=%s,ville=%s,demande=%s" % (nom, cp, ville, demande))

    update_companies_latlng()
