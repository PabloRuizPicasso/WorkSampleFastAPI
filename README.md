### Описание:


API будет доступен на `http://localhost:8000`  
Документация: `http://localhost:8000/docs` (Swagger) или `/redoc`


### Для запуска, пошагово:

#### Установить Docker (если не установлен):
>https://docs.docker.com/engine/install/#installation-procedures-for-supported-platforms

#### Добавить пользователя в группу docker:

    sudo usermod -aG docker username

#### Клонировать репозиторий и перейти в него:
    git clone https://github.com/PabloRuizPicasso/WorkSampleFastAPI.git
    cd WorkSampleFastAPI
#### Собрать проект:

    docker compose build
    docker compose run --rm migrate

### Запустить:

    docker compose up