"""
Comando: python manage.py seed
Genera datos de demo para SyncTrip con Faker.
Usa --flush para borrar todos los datos antes de sembrar.
"""
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand
from django.db import transaction

from faker import Faker

from core.models import (
    Usuario, Viaje, Participa, SolicitudAmistad,
    GrupoChat, MensajeGrupoChat,
    Gasto, GastoSplit, ParticipanteGasto,
)

fake = Faker("es_ES")
random.seed(42)

# ── Destinos ────────────────────────────────────────────────────────────────
DESTINOS = [
    ("Barcelona",      "España"),
    ("París",          "Francia"),
    ("Roma",           "Italia"),
    ("Londres",        "Reino Unido"),
    ("Amsterdam",      "Países Bajos"),
    ("Lisboa",         "Portugal"),
    ("Tokio",          "Japón"),
    ("Nueva York",     "Estados Unidos"),
    ("Cancún",         "México"),
    ("Buenos Aires",   "Argentina"),
    ("Berlín",         "Alemania"),
    ("Praga",          "República Checa"),
    ("Dubái",          "Emiratos Árabes"),
    ("Bangkok",        "Tailandia"),
    ("Marrakech",      "Marruecos"),
    ("Ámsterdam",      "Países Bajos"),
    ("Viena",          "Austria"),
    ("Estambul",       "Turquía"),
    ("Seúl",           "Corea del Sur"),
    ("Ciudad de México","México"),
    ("Florencia",      "Italia"),
    ("Edimburgo",      "Escocia"),
    ("Atenas",         "Grecia"),
    ("Reikiavik",      "Islandia"),
]

ORIGENES = [
    ("Madrid",     "España"),
    ("Barcelona",  "España"),
    ("Valencia",   "España"),
    ("Sevilla",    "España"),
    ("Bilbao",     "España"),
    ("Zaragoza",   "España"),
    ("Málaga",     "España"),
]

NOMBRES_GASTOS = [
    "Vuelos", "Hotel", "Airbnb", "Cena restaurante", "Comida supermercado",
    "Alquiler coche", "Transporte público", "Entradas museo", "Excursión",
    "Seguro viaje", "Actividad aventura", "Cena de despedida", "Desayunos",
    "Taxi aeropuerto", "Souvenirs", "Spa", "Concierto", "Ferry",
    "Entrada parque temático", "Tour guiado", "Cena romántica", "Kayak",
]

MENSAJES_CHAT = [
    "¿A qué hora quedamos en el aeropuerto?",
    "He encontrado un restaurante muy bueno cerca del hotel 🍕",
    "¿Alguien necesita adaptar el equipaje?",
    "Confirmo mi asistencia al plan de mañana",
    "Acabo de hacer el check-in online",
    "¿Cuál es la dirección exacta del Airbnb?",
    "El tiempo allí parece bueno para la semana que vamos 🌞",
    "He mirado el transporte desde el aeropuerto, hay metro directo",
    "Propongo visitar el mercado el primer día",
    "¿Reservamos la cena del sábado con antelación?",
    "Acabo de pagar el vuelo, os paso el justificante",
    "Genial! Esto va a ser un viajazo 🎉",
    "¿Llevamos efectivo o con tarjeta va bien?",
    "He actualizado el itinerario con los horarios",
    "Perfecto, nos vemos en la terminal 2",
    "¿Alguien ha estado antes en este destino?",
    "He visto que hay huelga de transporte esos días, ojo",
    "¡Ya tengo el visado aprobado! 🙌",
    "¿Hacemos una lista de cosas que llevar?",
    "El hotel tiene piscina, ya me estoy imaginando 🏊",
    "¿Podemos quedar antes para hacer las maletas juntos?",
    "He mirado el cambio de moneda, conviene llevar algo en efectivo",
    "Acabo de ver que el museo cierra los lunes, planificad bien",
    "¿Alguien se apunta al tour de street food?",
    "Confirmo que tengo el seguro médico de viaje contratado",
    "El vuelo de vuelta sale a las 6am 😩 hay que madrugar",
    "Os mando la reserva del restaurante por aquí",
    "¡Qué ganas de que llegue ya!",
    "¿Hay que pagar propina en ese país?",
    "He leído que la mejor zona para alojarse es el centro histórico",
]

PASSWORD_DEMO = "demo1234"

# ── Datos fijos de usuarios ──────────────────────────────────────────────────
USUARIOS_DEMO = [
    ("ana_garcia",    "ana@demo.com",      "Ana",       "García López",       "1995-03-14"),
    ("carlos_mn",     "carlos@demo.com",   "Carlos",    "Martínez Núñez",     "1992-07-22"),
    ("sofia_rv",      "sofia@demo.com",    "Sofía",     "Rodríguez Vega",     "1998-11-05"),
    ("pablo_ft",      "pablo@demo.com",    "Pablo",     "Fernández Torres",   "1990-01-30"),
    ("lucia_sc",      "lucia@demo.com",    "Lucía",     "Sánchez Cano",       "1997-06-18"),
    ("miguel_op",     "miguel@demo.com",   "Miguel",    "Ortega Prieto",      "1993-09-09"),
    ("elena_br",      "elena@demo.com",    "Elena",     "Blanco Rubio",       "1996-04-25"),
    ("javier_dm",     "javier@demo.com",   "Javier",    "Díaz Morales",       "1991-12-03"),
    ("nuria_vg",      "nuria@demo.com",    "Nuria",     "Vargas Giménez",     "1999-08-17"),
    ("raul_ct",       "raul@demo.com",     "Raúl",      "Castro Torres",      "1994-02-28"),
    ("marta_pl",      "marta@demo.com",    "Marta",     "Pérez Llorente",     "1996-05-12"),
    ("david_ra",      "david@demo.com",    "David",     "Romero Aguilar",     "1993-10-07"),
    ("irene_hs",      "irene@demo.com",    "Irene",     "Herrero Santana",    "1998-01-23"),
    ("alex_mv",       "alex@demo.com",     "Alejandro", "Molina Vázquez",     "1991-07-15"),
    ("carmen_lg",     "carmen@demo.com",   "Carmen",    "López Guerrero",     "1997-03-30"),
    ("sergio_pn",     "sergio@demo.com",   "Sergio",    "Prieto Navarro",     "1990-11-19"),
    ("laura_jb",      "laura@demo.com",    "Laura",     "Jiménez Barroso",    "1995-09-04"),
    ("oscar_fm",      "oscar@demo.com",    "Óscar",     "Fuentes Medina",     "1992-06-11"),
]


class Command(BaseCommand):
    help = "Puebla la base de datos con datos de demo usando Faker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Borra todos los datos existentes antes de generar los nuevos.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("🗑️  Borrando datos existentes...")
            MensajeGrupoChat.objects.all().delete()
            GrupoChat.objects.all().delete()
            GastoSplit.objects.all().delete()
            ParticipanteGasto.objects.all().delete()
            Gasto.objects.all().delete()
            SolicitudAmistad.objects.all().delete()
            Participa.objects.all().delete()
            Viaje.objects.all().delete()
            Usuario.objects.all().delete()
            self.stdout.write("   Hecho.\n")

        # ── 1. USUARIOS ─────────────────────────────────────────────────────
        self.stdout.write("👤 Creando usuarios...")
        usuarios = []
        for username, correo, nombre, apellidos, nacimiento in USUARIOS_DEMO:
            if Usuario.objects.filter(username=username).exists():
                u = Usuario.objects.get(username=username)
                self.stdout.write(f"   ↩  {username} ya existe, reutilizando.")
            else:
                u = Usuario(
                    username=username,
                    correo=correo,
                    nombre=nombre,
                    apellidos=apellidos,
                    fecha_nacimiento=date.fromisoformat(nacimiento),
                )
                u.set_password(PASSWORD_DEMO)
                u.save()
                self.stdout.write(f"   ✓  {username}")
            usuarios.append(u)

        n = len(usuarios)

        # ── 2. AMISTADES ────────────────────────────────────────────────────
        self.stdout.write("\n🤝 Creando amistades...")
        pares_amigos = [
            (0,1),(0,2),(0,3),(0,9),(0,14),
            (1,2),(1,4),(1,10),(1,15),
            (2,5),(2,11),(2,16),
            (3,4),(3,6),(3,12),
            (4,5),(4,13),(4,17),
            (5,7),(5,14),
            (6,7),(6,8),(6,15),
            (7,9),(7,16),
            (8,9),(8,10),(8,17),
            (9,11),(9,13),
            (10,12),(10,14),
            (11,13),(11,15),
            (12,16),(13,17),
        ]
        creadas = 0
        for i, j in pares_amigos:
            if i >= n or j >= n:
                continue
            u1, u2 = usuarios[i], usuarios[j]
            if not SolicitudAmistad.objects.filter(emisor=u1, receptor=u2).exists() \
               and not SolicitudAmistad.objects.filter(emisor=u2, receptor=u1).exists():
                SolicitudAmistad.objects.create(
                    emisor=u1, receptor=u2,
                    estado=SolicitudAmistad.Estado.ACEPTADA,
                )
                creadas += 1
        self.stdout.write(f"   ✓  {creadas} amistades creadas")

        # ── 3. VIAJES ───────────────────────────────────────────────────────
        self.stdout.write("\n✈️  Creando viajes...")
        hoy = date.today()

        # (creador_idx, participantes_idx, destino_idx, delta_ida, duracion, precio, visibilidad, estado_forzado)
        config_viajes = [
            # --- PROGRAMADOS futuros públicos ---
            (0,  [1,2,3],      0,  25, 10, 350, "PUBLICO",  None),
            (1,  [0,4,10],     1,  40,  7, 180, "PUBLICO",  None),
            (2,  [5,11],       2,  55,  5, 220, "PUBLICO",  None),
            (3,  [0,1,7,12],   3,  18, 14, 900, "PUBLICO",  None),
            (4,  [13,14],     16,  70,  6, 410, "PUBLICO",  None),
            (5,  [6,15],      17,  35,  9, 275, "PUBLICO",  None),
            (6,  [2,16],      20,  80,  8, 160, "PUBLICO",  None),
            (7,  [3,9,17],    21,  45, 11, 590, "PUBLICO",  None),
            (8,  [0,14],      22,  60,  7, 340, "PUBLICO",  None),
            (9,  [1,5],       23,  90,  5, 480, "PUBLICO",  None),
            # --- PROGRAMADOS futuros privados ---
            (10, [0,1,2],      4,  30,  8, 195, "PRIVADO",  None),
            (11, [3,4,5],      5,  50, 10, 320, "PRIVADO",  None),
            (12, [6,7],        6,  65,  6, 440, "PRIVADO",  None),
            # --- EN CURSO ---
            (0,  [1,4,13],     7,  -2, 10, 150, "PUBLICO",  "EN_CURSO"),
            (2,  [5,6,15],     8,  -1,  7,  95, "PRIVADO",  "EN_CURSO"),
            (3,  [9,17],       9,  -3,  5, 260, "PUBLICO",  "EN_CURSO"),
            # --- FINALIZADOS ---
            (4,  [0,7,10],    10, -35,  8, 680, "PUBLICO",  "FINALIZADO"),
            (5,  [1,11],      11, -20,  5, 200, "PUBLICO",  "FINALIZADO"),
            (6,  [2,8,12],    12, -50, 12, 420, "PRIVADO",  "FINALIZADO"),
            (7,  [3,13],      13, -15,  4, 310, "PUBLICO",  "FINALIZADO"),
            (8,  [4,14,16],   14, -60,  9, 530, "PRIVADO",  "FINALIZADO"),
            (9,  [5,15],      15, -45,  7, 175, "PUBLICO",  "FINALIZADO"),
            # --- CANCELADOS ---
            (10, [],          18,  20,  6, 310, "PUBLICO",  "CANCELADO"),
            (11, [0],         19,  10,  4, 240, "PUBLICO",  "CANCELADO"),
        ]

        viajes = []
        for (ci, parts, di, delta_ida, dur, precio, vis, estado_forzado) in config_viajes:
            creador = usuarios[ci % n]
            ciudad_d, pais_d = DESTINOS[di % len(DESTINOS)]
            ciudad_o, pais_o = random.choice(ORIGENES)
            fecha_ida    = hoy + timedelta(days=delta_ida)
            fecha_vuelta = fecha_ida + timedelta(days=dur)

            viaje = Viaje.objects.create(
                ciudad_origen=ciudad_o,
                pais_origen=pais_o,
                ciudad_destino=ciudad_d,
                pais_destino=pais_d,
                fecha_ida=fecha_ida,
                fecha_vuelta=fecha_vuelta,
                direccion_encuentro=fake.address()[:200],
                precio_persona=Decimal(precio),
                visibilidad=vis,
                estado_viaje=estado_forzado or Viaje.EstadoViaje.PROGRAMADO,
                creador=creador,
            )
            viaje.participantes.add(creador)
            for pi in parts:
                if pi < n:
                    viaje.participantes.add(usuarios[pi])

            viajes.append(viaje)
            tag = estado_forzado or "PROGRAMADO"
            self.stdout.write(f"   ✓  {ciudad_d} ({vis}, {tag})")

        # ── 4. GASTOS (viajes privados con ≥2 participantes) ────────────────
        self.stdout.write("\n💶 Creando gastos...")
        total_gastos = 0
        for viaje in viajes:
            if viaje.visibilidad != Viaje.Visibilidad.PRIVADO:
                continue
            participantes = list(viaje.participantes.all())
            if len(participantes) < 2:
                continue

            num_gastos = random.randint(4, 8)
            for _ in range(num_gastos):
                importe = Decimal(random.randint(15, 600))
                pagador = random.choice(participantes)
                gasto = Gasto.objects.create(
                    viaje=viaje,
                    pagador=pagador,
                    nombre=random.choice(NOMBRES_GASTOS),
                    descripcion=fake.sentence(nb_words=7),
                    importe_total=importe,
                )
                ParticipanteGasto.objects.bulk_create([
                    ParticipanteGasto(gasto=gasto, usuario=u) for u in participantes
                ])
                nn = len(participantes)
                parte = (importe / nn).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                splits = [parte] * nn
                ajuste = importe - parte * nn
                splits[0] = (splits[0] + ajuste).quantize(Decimal("0.01"))
                GastoSplit.objects.bulk_create([
                    GastoSplit(gasto=gasto, usuario=participantes[i], importe=splits[i])
                    for i in range(nn)
                ])
                total_gastos += 1

        self.stdout.write(f"   ✓  {total_gastos} gastos creados")

        # ── 5. CHATS DE GRUPO (públicos Y privados) ─────────────────────────
        self.stdout.write("\n💬 Creando chats de grupo...")
        total_msgs = 0
        for viaje in viajes:
            participantes = list(viaje.participantes.all())
            if len(participantes) < 2:
                continue
            if GrupoChat.objects.filter(viaje=viaje).exists():
                continue

            grupo = GrupoChat.objects.create(
                viaje=viaje,
                creado_por=viaje.creador,
                nombre=f"Chat {viaje.ciudad_destino}",
            )
            num_msgs = random.randint(6, 18)
            for _ in range(num_msgs):
                MensajeGrupoChat.objects.create(
                    grupo=grupo,
                    autor=random.choice(participantes),
                    contenido=random.choice(MENSAJES_CHAT),
                )
                total_msgs += 1
            self.stdout.write(
                f"   ✓  Chat '{grupo.nombre}' ({viaje.visibilidad}) — {num_msgs} mensajes"
            )

        # ── Resumen ──────────────────────────────────────────────────────────
        self.stdout.write("\n" + "─" * 55)
        self.stdout.write(self.style.SUCCESS("✅ Seed completado"))
        self.stdout.write(f"   Usuarios   : {Usuario.objects.count()}")
        self.stdout.write(f"   Viajes     : {Viaje.objects.count()}")
        self.stdout.write(f"   Amistades  : {SolicitudAmistad.objects.filter(estado='ACEPTADA').count()}")
        self.stdout.write(f"   Gastos     : {Gasto.objects.count()}")
        self.stdout.write(f"   Chats      : {GrupoChat.objects.count()}")
        self.stdout.write(f"   Mensajes   : {MensajeGrupoChat.objects.count()}")
        self.stdout.write(f"\n   🔑 Contraseña de todos los usuarios demo: {PASSWORD_DEMO}")
        self.stdout.write("─" * 55)
