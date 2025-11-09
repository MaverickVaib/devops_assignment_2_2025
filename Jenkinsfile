pipeline {
  agent any

  options {
    timestamps()
    ansiColor('xterm')
  }

  triggers {
    // pick one: either GitHub webhook or pollSCM. Leaving poll so it "just works".
    pollSCM('@hourly')
  }

  environment {
    DOCKERHUB_USER = 'maverickvaib'              // set your Docker Hub user
    IMAGE_NAME     = 'aceest-fitness'
    MINIKUBE_HOME  = "${env.WORKSPACE}/.minikube" // keep minikube data in workspace
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
        dir('flask') {
          script {
            env.VERSION   = sh(returnStdout: true, script: "tr -d '\\r' < version.txt").trim()
            env.SHORT_SHA = sh(returnStdout: true, script: "git rev-parse --short HEAD").trim()
            echo "Building version ${env.VERSION} (${env.SHORT_SHA})"
          }
        }
      }
    }

    stage('Set up Python & Install Deps') {
      steps {
        dir('flask') {
          sh '''
            set -e
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
        dir('flask') {
          sh '''
            set -e
            . .venv/bin/activate
            pytest --junitxml=test-results.xml --cov=aceest_fitness --cov-report=term-missing --cov-report=xml:coverage.xml
          '''
        }
      }
      post {
        always {
          junit 'flask/test-results.xml'
          // comment out if you don't have the coverage plugin installed
          // recordCoverage(tools: [[parser: 'JACOCO', pattern: 'flask/coverage.xml']])
        }
      }
    }

    stage('Build & Push Docker Image') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'dockerhub',               // << your Jenkins credentials ID
          usernameVariable: 'DOCKERHUB_USER_CI',
          passwordVariable: 'DOCKERHUB_PASSWORD'
        )]) {
          sh '''
            set -e
            SHORT_SHA=$(git rev-parse --short HEAD)
            VERSION=$(tr -d '\\r' < flask/version.txt)

            docker build -t docker.io/${DOCKERHUB_USER_CI}/${IMAGE_NAME}:${VERSION} \
                         -t docker.io/${DOCKERHUB_USER_CI}/${IMAGE_NAME}:${SHORT_SHA} \
                         -t docker.io/${DOCKERHUB_USER_CI}/${IMAGE_NAME}:latest .

            echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USER_CI" --password-stdin

            docker push docker.io/${DOCKERHUB_USER_CI}/${IMAGE_NAME}:${VERSION}
            docker push docker.io/${DOCKERHUB_USER_CI}/${IMAGE_NAME}:${SHORT_SHA}
            docker push docker.io/${DOCKERHUB_USER_CI}/${IMAGE_NAME}:latest
          '''
        }
      }
    }

    stage('K8s: Ensure Minikube up') {
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"

          command -v minikube >/dev/null || { echo "minikube not installed on agent"; exit 1; }

          if ! minikube -p minikube status >/dev/null 2>&1; then
            echo "Starting minikube with Docker driver..."
            minikube -p minikube start --driver=docker --cpus=2 --memory=4096 --disk-size=10g
          else
            echo "Minikube already running."
          fi

          minikube -p minikube status
        '''
      }
    }

    stage('Deploy (Rolling)') {
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"

          NS=ace
          SHORT_SHA=$(git rev-parse --short HEAD)
          IMG="docker.io/${DOCKERHUB_USER}/${IMAGE_NAME}:${SHORT_SHA}"

          # ensure namespace
          minikube -p minikube kubectl -- get ns "${NS}" >/dev/null 2>&1 || \
            minikube -p minikube kubectl -- create ns "${NS}"

          # base manifests
          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/base/service.yaml
          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/base/deployment.yaml

          # set image
          minikube -p minikube kubectl -- -n "${NS}" set image deploy/ace-api web="${IMG}"

          # rollout wait
          minikube -p minikube kubectl -- -n "${NS}" rollout status deploy/ace-api --timeout=180s

          # Smoke
          TYPE=$(minikube -p minikube kubectl -- -n "${NS}" get svc ace-api -o jsonpath='{.spec.type}')
          if echo "$TYPE" | grep -qi NodePort; then
            NODE_IP=$(minikube -p minikube ip)
            NODE_PORT=$(minikube -p minikube kubectl -- -n "${NS}" get svc ace-api -o jsonpath='{.spec.ports[0].nodePort}')
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://${NODE_IP}:${NODE_PORT}/api/health" || true)
            echo "Smoke /api/health => ${code}"
            test "${code}" = "200"
          else
            minikube -p minikube kubectl -- -n "${NS}" port-forward svc/ace-api 18080:80 >/tmp/pf.log 2>&1 &
            PF_PID=$!
            sleep 2
            code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:18080/api/health" || true)
            kill "${PF_PID}" || true
            echo "Smoke /api/health => ${code}"
            test "${code}" = "200"
          fi
        '''
      }
    }

    // Optional: BG / Canary / Shadow / A-B stages using minikube kubectl --
    stage('BG: Deploy Green') {
      when { expression { fileExists('k8s/strategies/bg/green.yaml') } }
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"
          NS=ace
          SHORT_SHA=$(git rev-parse --short HEAD)
          IMG="docker.io/${DOCKERHUB_USER}/${IMAGE_NAME}:${SHORT_SHA}"

          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/strategies/bg/green.yaml
          minikube -p minikube kubectl -- -n "${NS}" set image deploy/ace-api-green web="${IMG}"
          minikube -p minikube kubectl -- -n "${NS}" rollout status deploy/ace-api-green --timeout=180s
        '''
      }
    }

    stage('BG: Flip Service to Green + Smoke') {
      when { expression { fileExists('k8s/strategies/bg/svc-green.yaml') } }
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"
          NS=ace

          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/strategies/bg/svc-green.yaml

          NODE_IP=$(minikube -p minikube ip)
          NODE_PORT=$(minikube -p minikube kubectl -- -n "${NS}" get svc ace-api -o jsonpath='{.spec.ports[0].nodePort}')
          code=$(curl -s -o /dev/null -w "%{http_code}" "http://${NODE_IP}:${NODE_PORT}/api/health" || true)
          echo "BG Smoke => ${code}"
          test "${code}" = "200"
        '''
      }
    }

    stage('Canary: Deploy Stable + Canary') {
      when { expression { fileExists('k8s/strategies/canary/') } }
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"
          NS=ace
          SHORT_SHA=$(git rev-parse --short HEAD)
          IMG="docker.io/${DOCKERHUB_USER}/${IMAGE_NAME}:${SHORT_SHA}"

          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/strategies/canary/stable.yaml
          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/strategies/canary/canary.yaml
          minikube -p minikube kubectl -- -n "${NS}" set image deploy/ace-api-canary web="${IMG}"
          minikube -p minikube kubectl -- -n "${NS}" rollout status deploy/ace-api-canary --timeout=180s
        '''
      }
    }

    stage('Shadow: Mirror Traffic') {
      when { expression { fileExists('k8s/strategies/shadow/') } }
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"
          NS=ace

          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/strategies/shadow/ingress-shadow.yaml || true
        '''
      }
    }

    stage('A/B: Route Split') {
      when { expression { fileExists('k8s/strategies/ab/') } }
      steps {
        sh '''
          set -e
          export MINIKUBE_HOME="${MINIKUBE_HOME}"
          NS=ace
          minikube -p minikube kubectl -- -n "${NS}" apply -f k8s/strategies/ab/ingress-ab.yaml || true
        '''
      }
    }
  }

  post {
    always {
      sh 'rm -rf flask/.venv || true'
    }
    failure {
      echo 'CI failed. Fix tests or setup and push again.'
    }
  }
}
