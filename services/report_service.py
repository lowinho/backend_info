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
        Cria relatório completo de processamento
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
        """
        Retorna descrição em português.
        Atualizado para refletir as novas chaves do PIIDetector.
        """
        descriptions = {
            # --- Identificadores ---
            'CPF': 'Cadastro de Pessoa Física',
            'CNPJ': 'Cadastro Nacional de Pessoa Jurídica',
            'PERSON_NAME': 'Nome de Pessoa',
            
            # --- Contatos e Localização ---
            'EMAIL': 'Endereço de E-mail',
            'PHONE': 'Número de Telefone',
            'FULL_ADDRESS': 'Endereço Completo',
            'CEP': 'Código de Endereçamento Postal',

            # --- Documentos Diversos (Agora inclui GENERAL_REGISTRY) ---
            'GENERAL_REGISTRY': 'Registros Gerais (RG/NIS/PIS/CNH)',
            'DOC_GENERICO': 'Documento Genérico', 
            'MATRICULA': 'Matrícula Funcional',
            'OAB': 'Registro OAB',
            'CREDIT_CARD': 'Número de Cartão de Crédito',
            
            # --- Dados Sensíveis (Atualizado) ---
            'SENSITIVE_HEALTH': 'Dados de Saúde (Sensível)',
            'SENSITIVE_MINOR': 'Dados de Menor de Idade (Sensível)',
            'SENSITIVE_SOCIAL': 'Dados Sociais (Sensível)',
            'SENSITIVE_RACE': 'Dados de Raça/Cor (Sensível)',
            'SENSITIVE_GENDER': 'Dados de Gênero (Sensível)',
            
            'DATE_BIRTH': 'Data de Nascimento'
        }
        return descriptions.get(pii_type, pii_type)
    
    @staticmethod
    def _calculate_risk_level(pii_stats: Dict[str, int], total_records: int) -> str:
        """
        Calcula nível de risco.
        Atualizado para considerar Raça e Gênero como CRÍTICO.
        """
        critical_pii = {
            'CPF', 'CNPJ', 'GENERAL_REGISTRY', 'CREDIT_CARD',
            'SENSITIVE_HEALTH', 'SENSITIVE_MINOR', 'SENSITIVE_SOCIAL', 
            'SENSITIVE_RACE', 'SENSITIVE_GENDER'
        }
        
        high_risk_pii = {
            'EMAIL', 'PHONE', 'DATE_BIRTH', 'OAB', 'MATRICULA', 'FULL_ADDRESS'
        }
        
        critical_count = sum(pii_stats.get(pii, 0) for pii in critical_pii)
        high_count = sum(pii_stats.get(pii, 0) for pii in high_risk_pii)
        total_pii = sum(pii_stats.values())
        
        if critical_count > 0:
            # Qualquer dado sensível já eleva para crítico
            sensitive_detected = any(k in pii_stats for k in [
                'SENSITIVE_HEALTH', 'SENSITIVE_RACE', 'SENSITIVE_GENDER', 'SENSITIVE_MINOR'
            ])
            if (critical_count / total_records > 0.05) or sensitive_detected:
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
            'CRÍTICO': 'Dados sensíveis (Saúde/Raça/Gênero) ou identificadores oficiais detectados.',
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
        
        if 'SENSITIVE_HEALTH' in pii_stats:
            recommendations.append('ALERTA: Dado Sensível de Saúde. Requer Relatório de Impacto (RIPD/DPIA)')
            
        if 'SENSITIVE_RACE' in pii_stats or 'SENSITIVE_GENDER' in pii_stats:
            recommendations.append('ALERTA: Dados Discriminatórios (Raça/Gênero) detectados. Tratamento restrito.')

        if 'CPF' in pii_stats or 'GENERAL_REGISTRY' in pii_stats:
            recommendations.append('Identificadores governamentais: Aplicar mascaramento irreversível para ambientes de teste')
        
        if not recommendations:
            recommendations.append('Manter monitoramento periódico')
        
        return recommendations