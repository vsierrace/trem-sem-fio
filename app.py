import streamlit as st
from streamlit_autorefresh import st_autorefresh

import json
import os
import uuid
import random
import qrcode
import time

from io import BytesIO

# =====================================
# CONFIG
# =====================================

st.set_page_config(
    page_title="Project Telephone",
    layout="wide"
)

st_autorefresh(
    interval=3000,
    key="refresh"
)

DB_FILE = "data.json"
ROUND_TIME = 15

BASE_URL = "https://project-telephone.streamlit.app"

BASE_URL = BASE_URL.rstrip("/")

# =====================================
# STORAGE
# =====================================

def load_data():

    if not os.path.exists(DB_FILE):

        return {
            "rooms": {}
        }

    with open(
        DB_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_data(data):

    with open(
        DB_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


data = load_data()

# =====================================
# HELPERS
# =====================================

def preservation_score(original, final):

    original_words = set(
        original.lower().split()
    )

    final_words = set(
        final.lower().split()
    )

    if len(original_words) == 0:
        return 0

    common = (
        original_words &
        final_words
    )

    return round(
        (
            len(common)
            / len(original_words)
        ) * 100,
        1
    )

# =====================================
# QR
# =====================================

def generate_qr(url):

    qr = qrcode.QRCode(
        box_size=10,
        border=2
    )

    qr.add_data(url)

    qr.make(fit=True)

    img = qr.make_image()

    buffer = BytesIO()

    img.save(
        buffer,
        format="PNG"
    )

    return buffer.getvalue()

# =====================================
# QUERY PARAMS
# =====================================

params = st.query_params

default_mode = params.get(
    "mode",
    "host"
)

default_room = params.get(
    "room",
    ""
)

# =====================================
# MENU
# =====================================

mode_map = {
    "host": "Host",
    "player": "Participante",
    "dashboard": "Dashboard"
}

mode = st.sidebar.selectbox(
    "Modo",
    ["Host", "Participante", "Dashboard"],
    index=[
        "Host",
        "Participante",
        "Dashboard"
    ].index(
        mode_map.get(
            params.get("mode", "host"),
            "Host"
        )
    )
)

st.title("📞 Project Telephone")

# =====================================
# HOST
# =====================================

if mode == "Host":

    st.header("Criar Sala")

    requirements_text = st.text_area(
        "Requisitos (1 por linha)",
        value="""
O sistema deverá detectar perda de comunicação em até 2 segundos e entrar em modo seguro.
Toda falha crítica deve gerar alarme em até 3 segundos.
Toda configuração deve ser rastreável.
A disponibilidade deverá ser superior a 99,5%.
Toda falha crítica deve ser registrada em log.
"""
    )

    if st.button("Criar Sala"):

        room_id = (
            str(uuid.uuid4())[:6]
            .upper()
        )

        reqs = [
            x.strip()
            for x in requirements_text.split("\n")
            if x.strip()
        ]

        data["rooms"][room_id] = {

            "started": False,

            "requirements": reqs,

            "players": [],

            "chains": []
        }

        save_data(data)

        st.session_state.room = room_id

    room_id = st.text_input(
        "Código da Sala",
        st.session_state.get(
            "room",
            ""
        )
    ).upper()

    if room_id in data["rooms"]:

        room = data["rooms"][room_id]

        participant_url = (
            f"{BASE_URL}/"
            f"?mode=player"
            f"&room={room_id}"
        )

        st.success(
            f"Sala: {room_id}"
        )

        qr = generate_qr(
            participant_url
        )

        col1,col2 = st.columns(
            [2,1]
        )

        with col1:

            st.code(
                participant_url
            )

        with col2:

            st.image(
                qr,
                width=300
            )

        st.subheader(
            "Participantes"
        )

        if st.button(
            "🗑️ Excluir Sala"
        ):

            del data["rooms"][
                room_id
            ]

            save_data(data)

            st.success(
                "Sala removida"
            )

            st.rerun()

        for p in room["players"]:

            st.write(
                "✅",
                p
            )

        if (
            not room["started"]
            and len(room["players"]) >= 2
        ):

            if st.button(
                "🚀 Iniciar"
            ):

                players = (
                    room["players"][:]
                )

                random.shuffle(
                    players
                )

                target_size = 7 #trocar participantes

                chain_count = max(
                    1,
                    round(
                        len(players)
                        / target_size
                    )
                )

                room["chains"] = []

                idx = 0

                for c in range(
                    chain_count
                ):

                    remaining = (
                        len(players)
                        - idx
                    )

                    remaining_groups = (
                        chain_count - c
                    )

                    size = max(
                        1,
                        round(
                            remaining
                            /
                            remaining_groups
                        )
                    )

                    members = players[
                        idx:idx+size
                    ]

                    req = (
                        room["requirements"][
                            c %
                            len(
                                room[
                                    "requirements"
                                ]
                            )
                        ]
                    )

                    room["chains"].append({

                        "players":
                        members,

                        "current":
                        0,

                        "finished":
                        False,

                        "history":[
                            {
                                "author":
                                "ORIGINAL",
                                "text":
                                req
                            }
                        ]
                    })

                    idx += size

                room["started"] = True

                save_data(data)

                st.rerun()

        if room["started"]:

            st.divider()

            st.subheader(
                "Progresso"
            )

            for i,chain in enumerate(
                room["chains"]
            ):

                st.write(
                    f"Cadeia {i+1}: "
                    f"{chain['current']}/"
                    f"{len(chain['players'])}"
                )

            st.divider()

            st.subheader(
                "Resultados"
            )

            ranking = []

            for idx,chain in enumerate(
                room["chains"]
            ):

                score = preservation_score(
                    chain["history"][0]["text"],
                    chain["history"][-1]["text"]
                )

                ranking.append(
                    (
                        idx + 1,
                        score
                    )
                )

            ranking.sort(
                key=lambda x: x[1],
                reverse=True
            )

            st.subheader(
                "🏆 Ranking"
            )

            for pos,item in enumerate(
                ranking
            ):

                chain_id,score = item

                medal = ["🥇","🥈","🥉"]

                icon = (
                    medal[pos]
                    if pos < 3
                    else "🏅"
                )

                st.write(
                    f"{icon} Cadeia {chain_id} "
                    f"- {score}%"
                )

            st.divider()

            for i,chain in enumerate(
                room["chains"]
            ):

                st.markdown(
                    f"## Cadeia {i+1}"
                )

                original = chain["history"][0]["text"]

                final = chain["history"][-1]["text"]

                score = preservation_score(
                    original,
                    final
                )

                st.metric(
                    "Preservação",
                    f"{score}%"
                )

                for idx,item in enumerate(
                    chain["history"]
                ):

                    if idx > 0:
                        st.markdown("⬇️")

                    st.markdown(
                        f"### {item['author']}"
                    )

                    st.info(
                        item["text"]
                    )

# =====================================
# PARTICIPANTE
# =====================================

elif mode == "Participante":

    room_id = st.text_input(
        "Código",
        value=st.session_state.get(
            "room_id",
            default_room
        )
    ).upper()

    if room_id:
        st.session_state[
            "room_id"
        ] = room_id

    name = st.text_input(
        "Nome",
        value=st.session_state.get(
            "player_name",
            ""
        )
    )

    if name:
        st.session_state[
            "player_name"
        ] = name

    if st.button("Entrar"):

        if room_id in data["rooms"]:

            room = data["rooms"][
                room_id
            ]

            if (
                name
                and
                name not in room["players"]
            ):

                room["players"].append(
                    name
                )

                save_data(data)

                st.success(
                    "Entrou!"
                )

    if room_id in data["rooms"]:

        room = data["rooms"][
            room_id
        ]

        if not room["started"]:

            st.info(
                "Aguardando host iniciar..."
            )

        else:

            my_chain = None
            my_position = None

            for chain in room["chains"]:

                if (
                    name
                    in
                    chain["players"]
                ):

                    my_chain = chain

                    my_position = (
                        chain[
                            "players"
                        ].index(
                            name
                        )
                    )

                    break

            if my_chain:

                if my_chain["finished"]:

                    st.success(
                        "Cadeia concluída."
                    )

                elif (
                    my_chain["current"]
                    ==
                    my_position
                ):

                    st.success(
                        "Sua vez"
                    )

                    previous_text = (
                        my_chain[
                            "history"
                        ][-1]["text"]
                    )

                    st.info(
                        previous_text
                    )

                    timer_key = (
                        f"{room_id}_"
                        f"{my_position}"
                    )

                    if (
                        timer_key
                        not in
                        st.session_state
                    ):

                        st.session_state[
                            timer_key
                        ] = time.time()

                    elapsed = int(
                        time.time()
                        -
                        st.session_state[
                            timer_key
                        ]
                    )

                    remaining = max(
                        0,
                        ROUND_TIME
                        - elapsed
                    )

                    st.metric(
                        "Tempo",
                        f"{remaining}s"
                    )

                    answer = (
                        st.text_area(
                            "Resuma ou explique para a próxima pessoa"
                        )
                    )

                    auto = (
                        remaining == 0
                    )

                    if (
                        st.button(
                            "Enviar"
                        )
                        or auto
                    ):

                        if not answer:

                            answer = (
                                "[SEM RESPOSTA]"
                            )

                        my_chain[
                            "history"
                        ].append(
                            {
                                "author":
                                name,
                                "text":
                                answer
                            }
                        )

                        my_chain[
                            "current"
                        ] += 1

                        if (
                            my_chain[
                                "current"
                            ]
                            >=
                            len(
                                my_chain[
                                    "players"
                                ]
                            )
                        ):

                            my_chain[
                                "finished"
                            ] = True

                        save_data(data)

                        st.rerun()

                else:

                    waiting = (
                        my_chain[
                            "players"
                        ][
                            my_chain[
                                "current"
                            ]
                        ]
                    )

                    st.info(
                        f"Aguardando {waiting}"
                    )

                    st.write(
                        f"Você é o participante "
                        f"{my_position + 1}"
                        f" de "
                        f"{len(my_chain['players'])}"
                    )

# =====================================
# DASHBOARD
# =====================================

else:

    st.header(
        "Dashboard"
    )

    room_id = st.text_input(
        "Código da Sala"
    ).upper()

    if room_id in data["rooms"]:

        room = data["rooms"][
            room_id
        ]

        total_players = len(
            room["players"]
        )

        total_chains = len(
            room["chains"]
        )

        finished = len([
            x
            for x in room["chains"]
            if x["finished"]
        ])

        c1,c2,c3 = st.columns(
            3
        )

        c1.metric(
            "Participantes",
            total_players
        )

        c2.metric(
            "Cadeias",
            total_chains
        )

        c3.metric(
            "Concluídas",
            finished
        )

        progress = 0

        if total_chains > 0:

            progress = (
                finished
                /
                total_chains
            )

        st.progress(
            progress
        )
