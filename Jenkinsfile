
pipeline {
  agent any

  environment {
    APP_DIR = 'flask'
    KUBECONFIG    = '/var/lib/jenkins/.kube/config'
    DOCKERHUB_USER = 'maverickvaib'
    IMAGE_NAME     = 'aceest-fitness'
  }

  options {
    timestamps()
    ansiColor('xterm')
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
        withCredentials([usernamePassword(
          credentialsId: 'maverickvaib',
          usernameVariable: 'DOCKERHUB_USER',
          passwordVariable: 'DOCKERHUB_PASSWORD')]) {
          sh '''
            set -e
                    IMAGE_NAME="aceest-fitness"
                    VERSION=$(tr -d '\\r' < flask/version.txt)
                    SHORT_SHA=$(git rev-parse --short HEAD)
                    IMG_BASE="docker.io/${DOCKERHUB_USER}/${IMAGE_NAME}"

                    echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USER" --password-stdin

                    docker build -t "${IMG_BASE}:${VERSION}" \
                                -t "${IMG_BASE}:${SHORT_SHA}" \
                                -t "${IMG_BASE}:latest" .

                    docker push "${IMG_BASE}:${VERSION}"
                    docker push "${IMG_BASE}:${SHORT_SHA}"
                    docker push "${IMG_BASE}:latest"

                    

                      '''
        }
      }
    }

    stage('Deploy (Rolling)') {
      steps {
        sh '''
          set -e

          NS=ace
          SHORT_SHA=$(git rev-parse --short HEAD)

          echo "Expecting: docker.io/${DOCKERHUB_USER}/aceest-fitness:${SHORT_SHA}"
          IMG="docker.io/${DOCKERHUB_USER}/aceest-fitness:${SHORT_SHA}"

          # Ensure base objects exist
          kubectl -n "$NS" apply -f k8s/base/service.yaml
          kubectl -n "$NS" apply -f k8s/base/deployment.yaml

          # Roll to the new image
          kubectl -n "$NS" set image deploy/ace-api web="$IMG"
          kubectl -n "$NS" rollout status deploy/ace-api --timeout=120s

          # Smoke test via NodePort
          NODE_IP=$(kubectl get node -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
          code=$(curl -s -o /dev/null -w "%{http_code}" "http://$NODE_IP:30080/api/health")
          echo "Smoke HTTP $code"
          [ "$code" = "200" ] || { kubectl -n "$NS" rollout undo deploy/ace-api; exit 1; }
          
        '''
      }
}

    stage('BG: Deploy Green') {
  steps {
    sh '''
      set -e

      NS=ace
      SHORT_SHA=$(git rev-parse --short HEAD)
      IMG="docker.io/${DOCKERHUB_USER}/aceest-fitness:${SHORT_SHA}"

      # Apply or update green deployment with current image
      # Replace image inline to avoid maintaining many YAML copies
      sed "s#image: .*#image: ${IMG}#g" k8s/strategies/blue-green/deploy-green.yaml | kubectl -n "$NS" apply -f -
      kubectl -n "$NS" rollout status deploy/ace-api-green --timeout=120s
    '''
  }
}

stage('BG: Flip Service to Green + Smoke') {
  steps {
    sh '''
      set -e
      
      NS=ace
      IP=$(minikube ip)

      # Flip selector to green
      kubectl -n "$NS" patch svc ace-api -p '{"spec":{"selector":{"app":"ace-api","track":"green"}}}'

      # Smoke test
      code=$(curl -s -o /dev/null -w "%{http_code}" http://$IP:30080/api/health)
      echo "Smoke after flip: HTTP ${code}"
      if [ "$code" != "200" ]; then
        echo "Flip failed, rolling back to blue"
        kubectl -n "$NS" patch svc ace-api -p '{"spec":{"selector":{"app":"ace-api","track":"blue"}}}'
        exit 1
      fi
    '''
  }
  post {
    success {
      echo 'Green is live.'
    }
  }
}

stage('Canary: Deploy Stable + Canary') {
  steps {
    sh '''
      set -e
      
      NS=ace
      SHORT_SHA=$(git rev-parse --short HEAD)
      IMG="docker.io/${DOCKERHUB_USER}/aceest-fitness:${SHORT_SHA}"

      # Apply stable (old) and canary (new)
      kubectl -n "$NS" apply -f k8s/strategies/canary/deploy-stable.yaml
      sed "s#image: .*#image: ${IMG}#g" k8s/strategies/canary/deploy-canary.yaml | kubectl -n "$NS" apply -f -
      kubectl -n "$NS" apply -f k8s/strategies/canary/service.yaml

      kubectl -n "$NS" rollout status deploy/ace-api-stable --timeout=120s
      kubectl -n "$NS" rollout status deploy/ace-api-canary --timeout=120s
    '''
  }
}

stage('Canary: 10% Traffic Smoke') {
  steps {
    sh '''
      set -e
      
      NS=ace
      # give canary tiny weight (1 pod) vs stable (e.g., 9 pods) if you want real 10%
      kubectl -n "$NS" scale deploy/ace-api-stable --replicas=9 || true
      kubectl -n "$NS" scale deploy/ace-api-canary --replicas=1 || true

      NODE_IP=$(kubectl get node -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
      code=$(curl -s -o /dev/null -w "%{http_code}" "http://$NODE_IP:30080/api/health")
      echo "Smoke HTTP $code"
      [ "$code" = "200" ] || { kubectl -n "$NS" rollout undo deploy/ace-api; exit 1; }
    '''
  }
}

stage('Canary: Promote to 100% or Rollback') {
  steps {
    sh '''
      set -e
      
      NS=ace
      PROMOTE=${PROMOTE:-yes}  # change via Jenkins parameter later if you want manual gate
      if [ "$PROMOTE" = "yes" ]; then
        echo "Promoting canary to 100%"
        kubectl -n "$NS" scale deploy/ace-api-stable --replicas=0
        kubectl -n "$NS" scale deploy/ace-api-canary --replicas=3
      else
        echo "Rolling back canary"
        kubectl -n "$NS" scale deploy/ace-api-canary --replicas=0
      fi
    '''
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
