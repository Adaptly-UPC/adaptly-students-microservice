def get_degree_by_number(degree_value):
    """Returns the degree name based on the degree number."""

    degree_number = degree_value
    if type(degree_value) is not int:
        degree_number = int(degree_value)

    degrees = {
        1: "PRIMERO",
        2: "SEGUNDO",
        3: "TERCERO",
        4: "CUARTO",
        5: "Quinto",
        6: "SEXTO"
    }

    return degrees.get(degree_number, "Desconocido")