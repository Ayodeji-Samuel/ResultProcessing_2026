pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    environment {
        APP_NAME       = "cschub"
        BASE_DIR       = "/var/www/cschub"
        RELEASES_DIR   = "/var/www/cschub/releases"
        CURRENT_LINK   = "/var/www/cschub/current"
        SERVICE_NAME   = "cschub"
    }

    stages {

        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Create Release Directory') {
            steps {
                script {
                    def timestamp = sh(
                        script: "date +%Y%m%d%H%M%S",
                        returnStdout: true
                    ).trim()

                    env.NEW_RELEASE = "${RELEASES_DIR}/${timestamp}"

                    sh """
                        mkdir -p ${NEW_RELEASE}
                        rsync -av --exclude='.git' ./ ${NEW_RELEASE}/
                    """
                }
            }
        }

        stage('Create Virtualenv & Install Dependencies') {
            steps {
                sh """
                    cd ${NEW_RELEASE}
                    . /var/www/cschub/venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                """
            }
        }

        stage('Switch Symlink') {
            steps {
                sh """
                    ln -sfn ${NEW_RELEASE} ${CURRENT_LINK}
                """
            }
        }

        stage('Run Migrations') {
            steps {
                sh """
                    cd ${CURRENT_LINK}
                    . /var/www/cschub/venv/bin/activate
                    python migrate_course_code_varchar20.py
                """
            }
        }

        stage('Restart Application') {
            steps {
                sh """
                    sudo systemctl restart ${SERVICE_NAME}
                """
            }
        }

        stage('Cleanup Old Releases') {
            steps {
                sh """
                    cd ${RELEASES_DIR}
                    ls -dt 20*/ | tail -n +6 | xargs -r rm -rf 
                """
            }
        }        
        
    }

    post {
        success {
            echo "Deployment successful."
        }
        failure {
            echo "Deployment failed."
        }
    }
}
