
# Transcripción Pacientes - Backend

Este es el backend de la aplicación **Transcripción Pacientes**, que se encarga de manejar las solicitudes de transcripción de audio en tiempo real utilizando **Google Cloud Speech-to-Text**. El backend está desarrollado en **Python** usando **FastAPI** y se espera desplegar en **Heroku**.

## Estructura del Proyecto

transcripcion-pacientes-backend/
├── app/ │
├── main.py │
    └── utils/
├── .gitignore
├── requirements.txt
    └── README.md


## Tecnologías Utilizadas

- **Python 3.8+**
- **FastAPI**
- **Google Cloud Speech-to-Text**
- **Uvicorn** (para ejecutar la aplicación)

## Requisitos Previos

1. **Python 3.8 o superior** debe estar instalado en tu máquina.
2. Crea un proyecto en **Google Cloud Platform** y habilita la API de **Speech-to-Text**.
3. Descarga y configura las credenciales del servicio de Google Cloud.

## Instalación

1. Clona este repositorio:

   ```bash
   git clone https://github.com/your-username/transcripcion-pacientes-backend.git
