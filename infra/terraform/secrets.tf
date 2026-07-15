resource "aws_secretsmanager_secret" "jwt_secret" {
  name                    = "${var.project_name}-jwt-secret-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

resource "aws_secretsmanager_secret" "groq_api_key" {
  name                    = "${var.project_name}-groq-api-key-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "groq_api_key" {
  secret_id     = aws_secretsmanager_secret.groq_api_key.id
  secret_string = var.groq_api_key
}

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}-db-password-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "sentry_dsn" {
  count                   = var.sentry_dsn != "" ? 1 : 0
  name                    = "${var.project_name}-sentry-dsn-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "sentry_dsn" {
  count     = var.sentry_dsn != "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.sentry_dsn[0].id
  secret_string = var.sentry_dsn
}

resource "aws_secretsmanager_secret" "slack_webhook" {
  count                   = var.slack_webhook_url != "" ? 1 : 0
  name                    = "${var.project-name}-slack-webhook-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "slack_webhook" {
  count     = var.slack_webhook_url != "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.slack_webhook[0].id
  secret_string = var.slack_webhook_url
}
