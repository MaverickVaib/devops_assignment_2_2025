pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
  }

  environment {
    APP_DIR = 'flask'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'git --no-pager log --oneline -n 1'
      }
    }

    stage('Determine Version') {
      steps {
        dir("${APP_DIR}") {
          script {
            def ver = sh(returnStdout: true, script: "cat version.txt").trim()
            env.APP_VERSION = ver
            env.SHORT_SHA = sh(returnStdout: true, script: "git rev-parse --short HEAD").trim()
            echo "Building version ${env.APP_VERSION} (${env.SHORT_SHA})"
          }
        }
      }
    }

    stage('Set up Python & Install Deps') {
      steps {
        dir("${APP_DIR}") {
          sh '''
            python3 -m venv .venv
            . .venv/bin/activate
            pip install -U pip
            pip install -r requirements.txt
            pip install pytest pytest-cov
          '''
        }
      }
    }

    stage('Unit Tests') {
      steps {
        dir("${APP_DIR}") {
          sh '''
            . .venv/bin/activate
            pytest --junitxml=test-results.xml \
                   --cov=aceest_fitness \
                   --cov-report=term-missing \
                   --cov-report=xml:coverage.xml
          '''
        }
      }
      post {
        always {
          junit allowEmptyResults: true, testResults: "flask/test-results.xml"
        }
      }
    }

    stage('Build & Push Docker Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'maverickvaib',
          usernameVariable: 'DOCKERHUB_USER',
          passwordVariable: 'DOCKERHUB_PASSWORD')]) {
          sh '''
            set -e
            DH_USER="${DOCKERHUB_USER}"
            IMAGE_NAME="aceest-fitness"
            VERSION=$(tr -d '\\r' < flask/version.txt)
            SHORT_SHA=$(git rev-parse --short HEAD)

            docker build -t docker.io/$DH_USER/$IMAGE_NAME:$VERSION \
                        -t docker.io/$DH_USER/$IMAGE_NAME:$SHORT_SHA \
                        -t docker.io/$DH_USER/$IMAGE_NAME:latest .

            echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USER" --password-stdin

            docker push docker.io/$DH_USER/$IMAGE_NAME:$VERSION
            docker push docker.io/$DH_USER/$IMAGE_NAME:$SHORT_SHA
            docker push docker.io/$DH_USER/$IMAGE_NAME:latest
          '''
        }
      }
    }

    stage('Package Build Artifact') {
      steps {
        sh '''
          rm -rf build && mkdir -p build
          zip -r build/aceest-fitness-${APP_VERSION}-${SHORT_SHA}.zip flask -x "flask/.venv/*" "flask/__pycache__/*" "flask/**/__pycache__/*" "flask/.pytest_cache/*"
        '''
        archiveArtifacts artifacts: 'build/*.zip', fingerprint: true
      }
    }
  }

  post {
    success {
      echo "CI passed: ${env.APP_VERSION}-${env.SHORT_SHA}"
    }
    failure {
      echo "CI failed. Fix tests or setup and push again."
    }
    always {
      // tidy up local cache a bit
      sh 'rm -rf flask/.venv || true'
    }
  }
}
