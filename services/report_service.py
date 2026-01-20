from datetime import datetime
from typing import Dict

class ReportService:
    """Gera relatórios detalhados de processamento de PII"""
    
    @staticmethod
    def create_report(
        process_uuid: str,
        filename: str,
        file_type: str,
        total_records: int,
        pii_statistics: Dict[str, int],
        processing_time: float
    ) -> Dict:
        """
        Cria relatório completo de processamento (Standard Output)
        """
        
        # Calcular totais
        total_pii_detected = sum(pii_statistics.values())
        records_with_pii = sum(1 for count in pii_statistics.values() if count > 0)
        
        # Criar detalhamento por tipo de PII
        pii_breakdown = []
        for pii_type, count in sorted(pii_statistics.items(), key=lambda x: x[1], reverse=True):
            pii_breakdown.append({
                'type': pii_type,
                'description': ReportService._get_pii_description(pii_type),
                'count': count,
                'percentage': round((count / total_pii_detected * 100), 2) if total_pii_detected > 0 else 0
            })
        
        # Classificação de risco
        risk_level = ReportService._calculate_risk_level(pii_statistics, total_records)
        
        # Montar relatório mantendo estrutura original
        report = {
            'process_uuid': process_uuid,
            'created_at': datetime.now().isoformat(),
            'file_info': {
                'filename': filename,
                'file_type': file_type,
                'total_records': total_records
            },
            'processing_stats': {
                'processing_time_seconds': round(processing_time, 2),
                'records_per_second': round(total_records / processing_time, 2) if processing_time > 0 else 0,
                'total_pii_detected': total_pii_detected,
                'records_with_pii': records_with_pii,
                'records_without_pii': total_records - records_with_pii,
                'pii_rate_percentage': round((records_with_pii / total_records * 100), 2) if total_records > 0 else 0
            },
            'pii_breakdown': pii_breakdown,
            'risk_assessment': {
                'level': risk_level,
                'description': ReportService._get_risk_description(risk_level),
                'recommendations': ReportService._get_recommendations(risk_level, pii_statistics)
            },
            'lgpd_compliance': {
                'anonymization_applied': True,
                'data_minimization': total_pii_detected > 0,
                'sensitive_data_check': 'SENSITIVE_HEALTH' in pii_statistics,
                'processing_date': datetime.now().isoformat(),
                'retention_policy': 'Dados originais não armazenados - apenas versão anonimizada'
            }
        }
        
        return report
    
    @staticmethod
    def _get_pii_description(pii_type: str) -> str:
        """Retorna descrição em português, incluindo novos tipos"""
        descriptions = {
            'CPF': 'Cadastro de Pessoa Física',
            'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
            'RG': 'Registro Geral',
            'EMAIL': 'Endereço de E-mail',
            'PHONE': 'Número de Telefone',
            'CEP': 'Código de Endereçamento Postal',
            'CREDIT_CARD': 'Número de Cartão de Crédito',
            'SEI_PROCESS': 'Número de Processo SEI',
            'PERSON_NAME': 'Nome de Pessoa',
            'LOCATION': 'Endereço/Localização',
            'DATE_BIRTH': 'Data de Nascimento',
            # Novos tipos
            'MATRICULA': 'Matrícula Funcional (Servidor)',
            'OAB': 'Registro Profissional OAB',
            'CNH': 'Carteira Nacional de Habilitação',
            'TITULO_ELEITOR': 'Título de Eleitor',
            'NIS': 'NIS/PIS/PASEP',
            'SENSITIVE_HEALTH': 'Dados de Saúde (Sensível)',
            'MINOR_CONTEXT': 'Dados de Menor de Idade (Sensível)'
        }
        return descriptions.get(pii_type, pii_type)
    
    @staticmethod
    def _calculate_risk_level(pii_stats: Dict[str, int], total_records: int) -> str:
        """
        Calcula nível de risco. 
        Atualizado: Dados sensíveis (Saúde) e múltiplos IDs elevam para CRÍTICO.
        """
        # IDs fortes ou Dados Sensíveis (Art 5 LGPD)
        critical_pii = {
            'CPF', 'CNPJ', 'RG', 'CREDIT_CARD', 'CNH', 
            'SENSITIVE_HEALTH', 'MINOR_CONTEXT'
        }
        # IDs de contato ou profissionais
        high_risk_pii = {
            'EMAIL', 'PHONE', 'DATE_BIRTH', 'OAB', 'MATRICULA', 'TITULO_ELEITOR'
        }
        
        critical_count = sum(pii_stats.get(pii, 0) for pii in critical_pii)
        high_count = sum(pii_stats.get(pii, 0) for pii in high_risk_pii)
        total_pii = sum(pii_stats.values())
        
        # Lógica de Classificação
        if critical_count > 0:
            # Se mais de 5% dos registros tem dados críticos, ou se houver dado sensível
            if (critical_count / total_records > 0.05) or ('SENSITIVE_HEALTH' in pii_stats):
                return 'CRÍTICO'
            return 'ALTO'
        elif high_count > 0:
            return 'MÉDIO'
        elif total_pii > 0:
            return 'BAIXO'
        else:
            return 'MÍNIMO'
    
    @staticmethod
    def _get_risk_description(risk_level: str) -> str:
        descriptions = {
            'CRÍTICO': 'Dados sensíveis (Saúde/Menores) ou identificadores oficiais detectados em massa.',
            'ALTO': 'Identificadores oficiais e dados de contato detectados. Risco de identificação direta.',
            'MÉDIO': 'Dados profissionais ou de localização detectados.',
            'BAIXO': 'Poucos dados pessoais esparsos.',
            'MÍNIMO': 'Nenhum dado sensível significativo detectado.'
        }
        return descriptions.get(risk_level, 'Classificação não disponível')
    
    @staticmethod
    def _get_recommendations(risk_level: str, pii_stats: Dict[str, int]) -> list:
        recommendations = []
        
        if risk_level in ['CRÍTICO', 'ALTO']:
            recommendations.append('Implementar criptografia em repouso e trânsito')
            recommendations.append('Acesso restrito: Necessidade de conhecer (Need-to-know)')
        
        # Recomendação específica para dados sensíveis
        if 'SENSITIVE_HEALTH' in pii_stats:
            recommendations.append('ALERTA: Dado Sensível de Saúde. Requer Relatório de Impacto (RIPD/DPIA)')
        
        if 'MINOR_CONTEXT' in pii_stats:
            recommendations.append('ALERTA: Dados de menores detectados. Tratamento requer base legal específica.')

        if 'CPF' in pii_stats or 'RG' in pii_stats or 'CNH' in pii_stats:
            recommendations.append('Identificadores governamentais: Aplicar mascaramento irreversível para ambientes de teste')
        
        if not recommendations:
            recommendations.append('Manter monitoramento periódico')
        
        return recommendations