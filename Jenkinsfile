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
      credentialsId: 'maverickvaib',               
      usernameVariable: 'DOCKERHUB_USER',
      passwordVariable: 'DOCKERHUB_PASSWORD'
    )]) {
      sh '''
        set -e

        IMAGE_NAME="aceest-fitness"
        SHORT_SHA=$(git rev-parse --short HEAD)
        VERSION=$(tr -d '\\r' < flask/version.txt)

        IMG_BASE="docker.io/${DOCKERHUB_USER}/${IMAGE_NAME}"

        echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USER" --password-stdin

        docker build \
          -t "${IMG_BASE}:${VERSION}" \
          -t "${IMG_BASE}:${SHORT_SHA}" \
          -t "${IMG_BASE}:latest" .

        docker push "${IMG_BASE}:${VERSION}"
        docker push "${IMG_BASE}:${SHORT_SHA}"
        docker push "${IMG_BASE}:latest"
      '''
    }
  }
}

stage('K8s: Ensure Minikube up') {
  steps {
    sh '''
      set -eu
      export MINIKUBE_HOME="${MINIKUBE_HOME}"
      PROFILE="ace-mk"

      # If a half-dead cluster exists, nuke it to avoid zombie API servers
      minikube -p "$PROFILE" status >/dev/null 2>&1 || true
      if ! minikube -p "$PROFILE" status >/dev/null 2>&1; then
        echo "Starting minikube profile '$PROFILE' with Docker driver..."
        # Use a stable Kubernetes, wait for all components, and give it time
        minikube -p "$PROFILE" start \
          --driver=docker \
          --kubernetes-version=v1.30.0 \
          --cpus=2 --memory=4096 --disk-size=10g \
          --wait=all --wait-timeout=8m
      else
        echo "Minikube '$PROFILE' already running."
      fi

      # Robust wait for apiserver readiness (no more 'connection refused')
      for i in $(seq 1 60); do
        if minikube -p "$PROFILE" kubectl -- get --raw='/readyz?verbose' >/dev/null 2>&1; then
          echo "Kubernetes API is ready."
          break
        fi
        echo "Waiting for apiserver... ($i/60)"; sleep 3
      done

      # Basic sanity checks
      minikube -p "$PROFILE" kubectl -- get nodes
      minikube -p "$PROFILE" kubectl -- get ns
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

          minikube -p ace-mk kubectl -- -n "${NS}" apply -f k8s/strategies/bg/green.yaml
          minikube -p ace-mk kubectl -- -n "${NS}" set image deploy/ace-api-green web="${IMG}"
          minikube -p ace-mk kubectl -- -n "${NS}" rollout status deploy/ace-api-green --timeout=180s
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

          minikube -p ace-mk kubectl -- -n "${NS}" apply -f k8s/strategies/bg/svc-green.yaml

          NODE_IP=$(minikube -p ace-mk ip)
          NODE_PORT=$(minikube -p ace-mk kubectl -- -n "${NS}" get svc ace-api -o jsonpath='{.spec.ports[0].nodePort}')
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

          minikube -p ace-mk kubectl -- get ns "${NS}" >/dev/null 2>&1 || \
          minikube -p ace-mk kubectl -- create ns "${NS}"

          minikube -p ace-mk kubectl -- -n "${NS}" apply -f k8s/strategies/canary/stable.yaml
          minikube -p ace-mk kubectl -- -n "${NS}" apply -f k8s/strategies/canary/canary.yaml
          minikube -p ace-mk kubectl -- -n "${NS}" set image deploy/ace-api-canary web="${IMG}"
          minikube -p ace-mk kubectl -- -n "${NS}" rollout status deploy/ace-api-canary --timeout=180s
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

          minikube -p ace-mk kubectl -- -n "${NS}" apply -f k8s/strategies/shadow/ingress-shadow.yaml || true
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
          minikube -p ace-mk kubectl -- -n "${NS}" apply -f k8s/strategies/ab/ingress-ab.yaml || true
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
