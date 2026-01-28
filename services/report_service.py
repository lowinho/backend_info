from datetime import datetime
from typing import Dict

class ReportService:
    """
    Report Service V14.0 - Atualizado com novas categorias de PII
    """
    
    @staticmethod
    def create_report(
        process_uuid: str,
        filename: str,
        file_type: str,
        total_records: int,
        pii_statistics: Dict[str, int],
        processing_time: float,
        invalid_cpf_count: int = 0,
        records_with_pii_count: int = None
    ) -> Dict:
        
        total_pii_detected = sum(pii_statistics.values())
        if records_with_pii_count is not None:
            records_with_pii = records_with_pii_count
        else:
            records_with_pii = sum(1 for count in pii_statistics.values() if count > 0)
        
        pii_breakdown = []
        for pii_type, count in sorted(pii_statistics.items(), key=lambda x: x[1], reverse=True):
            pii_breakdown.append({
                'type': pii_type,
                'description': ReportService._get_pii_description(pii_type),
                'count': count,
                'percentage': round((count / total_pii_detected * 100), 2) if total_pii_detected > 0 else 0
            })
        
        risk_level = ReportService._calculate_risk_level(pii_statistics, total_records)
        
        quality_alerts = []
        if invalid_cpf_count > 0:
            quality_alerts.append({
                'type': 'INVALID_CPF',
                'severity': 'WARNING',
                'count': invalid_cpf_count,
                'message': f'Detectados {invalid_cpf_count} CPF(s) com formato inválido'
            })
        
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
            'data_quality': {
                'invalid_cpf_count': invalid_cpf_count,
                'alerts': quality_alerts
            }
        }
        
        return report
    
    @staticmethod
    def _get_pii_description(pii_type: str) -> str:
        descriptions = {
            'CPF': 'Cadastro de Pessoa Física',
            'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
            'RG': 'Registro Geral (RG)',
            'CNH': 'Carteira Nacional de Habilitação',
            'MATRICULA': 'Matrícula Funcional',
            'INSCRICAO': 'Inscrição (IPTU/Municipal)',
            'PERSON_NAME': 'Nome de Pessoa',
            'EMAIL': 'Endereço de E-mail',
            'PHONE': 'Número de Telefone',
            'FULL_ADDRESS': 'Endereço Completo',
            'CEP': 'Código de Endereçamento Postal',
            'LEGAL_PROCESS': 'Número de Processo',
            'SENSITIVE_HEALTH': 'Dados de Saúde (Sensível)',
            'SENSITIVE_MINOR': 'Dados de Menor de Idade (Sensível)',
            'SENSITIVE_SOCIAL': 'Dados Sociais (Sensível)',
            'SENSITIVE_RACE': 'Dados de Raça/Cor (Sensível)',
            'SENSITIVE_GENDER': 'Dados de Gênero (Sensível)'
        }
        return descriptions.get(pii_type, pii_type)
    
    @staticmethod
    def _calculate_risk_level(pii_stats: Dict[str, int], total_records: int) -> str:
        # ATUALIZADO V14: RG, CNH, MATRICULA são críticos
        critical_pii = {
            'CPF', 'RG', 'CNH', 'MATRICULA', 
            'SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 
            'SENSITIVE_RACE', 'SENSITIVE_GENDER'
        }
        
        high_risk_pii = {
            'EMAIL', 'PHONE', 'FULL_ADDRESS', 'INSCRICAO'
        }
        
        critical_count = sum(pii_stats.get(pii, 0) for pii in critical_pii)
        high_count = sum(pii_stats.get(pii, 0) for pii in high_risk_pii)
        
        if critical_count > 0:
            return 'CRÍTICO'
        elif high_count > 0:
            return 'MODERADO' # Mudamos de ALTO/MÉDIO para alinhar com o Hackathon
        elif sum(pii_stats.values()) > 0:
            return 'BAIXO'
        else:
            return 'PÚBLICO'
    
    @staticmethod
    def _get_risk_description(risk_level: str) -> str:
        descriptions = {
            'CRÍTICO': 'Documento contém dados sensíveis ou identificadores oficiais. NÃO DIVULGAR.',
            'MODERADO': 'Documento contém dados de contato ou inscrições secundárias. REVISAR.',
            'BAIXO': 'Dados pessoais esparsos encontrados.',
            'PÚBLICO': 'Nenhum dado pessoal identificado.'
        }
        return descriptions.get(risk_level, 'Classificação não disponível')
    
    @staticmethod
    def _get_recommendations(risk_level: str, pii_stats: Dict[str, int]) -> list:
        recommendations = []
        if risk_level == 'CRÍTICO':
            recommendations.append('Anonimização obrigatória ou retenção do documento.')
        if risk_level == 'MODERADO':
            recommendations.append('Verificar se dados de contato são institucionais ou pessoais.')
        return recommendations