"""
Serviço de geração de relatórios de processamento
"""
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
        
        Args:
            process_uuid: UUID único do processamento
            filename: Nome do arquivo processado
            file_type: Tipo do arquivo (csv/txt)
            total_records: Total de registros processados
            pii_statistics: Estatísticas de PII detectado
            processing_time: Tempo de processamento em segundos
            
        Returns:
            Dicionário com dados do relatório
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
        
        # Montar relatório
        report = {
            'process_uuid': process_uuid,
            'created_at': datetime.now().isoformat(),
            
            # Informações do arquivo
            'file_info': {
                'filename': filename,
                'file_type': file_type,
                'total_records': total_records
            },
            
            # Estatísticas de processamento
            'processing_stats': {
                'processing_time_seconds': round(processing_time, 2),
                'records_per_second': round(total_records / processing_time, 2) if processing_time > 0 else 0,
                'total_pii_detected': total_pii_detected,
                'records_with_pii': records_with_pii,
                'records_without_pii': total_records - records_with_pii,
                'pii_rate_percentage': round((records_with_pii / total_records * 100), 2) if total_records > 0 else 0
            },
            
            # Detalhamento por tipo de PII
            'pii_breakdown': pii_breakdown,
            
            # Análise de risco LGPD
            'risk_assessment': {
                'level': risk_level,
                'description': ReportService._get_risk_description(risk_level),
                'recommendations': ReportService._get_recommendations(risk_level, pii_statistics)
            },
            
            # Compliance LGPD
            'lgpd_compliance': {
                'anonymization_applied': True,
                'data_minimization': total_pii_detected > 0,
                'processing_date': datetime.now().isoformat(),
                'retention_policy': 'Dados originais não armazenados - apenas versão anonimizada'
            }
        }
        
        return report
    
    @staticmethod
    def _get_pii_description(pii_type: str) -> str:
        """Retorna descrição em português do tipo de PII"""
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
            'DATE_BIRTH': 'Data de Nascimento'
        }
        return descriptions.get(pii_type, pii_type)
    
    @staticmethod
    def _calculate_risk_level(pii_stats: Dict[str, int], total_records: int) -> str:
        """
        Calcula nível de risco baseado nos tipos de PII detectados
        
        Critérios:
        - CRÍTICO: CPF, CNPJ, RG, Cartão de Crédito
        - ALTO: E-mail, Telefone, Data de Nascimento
        - MÉDIO: CEP, Nome, Localização
        - BAIXO: Outros
        """
        critical_pii = {'CPF', 'CNPJ', 'RG', 'CREDIT_CARD'}
        high_risk_pii = {'EMAIL', 'PHONE', 'DATE_BIRTH'}
        
        critical_count = sum(pii_stats.get(pii, 0) for pii in critical_pii)
        high_count = sum(pii_stats.get(pii, 0) for pii in high_risk_pii)
        total_pii = sum(pii_stats.values())
        
        # Classificação
        if critical_count > 0:
            if critical_count / total_records > 0.5:
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
        """Retorna descrição do nível de risco"""
        descriptions = {
            'CRÍTICO': 'Dados altamente sensíveis detectados (CPF, RG, Cartão). Requer máxima proteção.',
            'ALTO': 'Dados sensíveis detectados. Atenção especial necessária.',
            'MÉDIO': 'Dados pessoais identificáveis detectados. Proteção adequada recomendada.',
            'BAIXO': 'Poucos dados sensíveis detectados. Risco controlável.',
            'MÍNIMO': 'Nenhum dado sensível significativo detectado.'
        }
        return descriptions.get(risk_level, 'Classificação não disponível')
    
    @staticmethod
    def _get_recommendations(risk_level: str, pii_stats: Dict[str, int]) -> list:
        """Gera recomendações baseadas no risco"""
        recommendations = []
        
        if risk_level in ['CRÍTICO', 'ALTO']:
            recommendations.append('Implementar criptografia adicional para armazenamento')
            recommendations.append('Restringir acesso aos dados apenas a usuários autorizados')
            recommendations.append('Implementar log de auditoria para todos os acessos')
        
        if 'CPF' in pii_stats or 'RG' in pii_stats:
            recommendations.append('Documentos de identificação detectados - considerar pseudonimização')
        
        if 'EMAIL' in pii_stats or 'PHONE' in pii_stats:
            recommendations.append('Dados de contato detectados - obter consentimento explícito para uso')
        
        if 'CREDIT_CARD' in pii_stats:
            recommendations.append('URGENTE: Dados financeiros detectados - validar compliance PCI-DSS')
        
        if not recommendations:
            recommendations.append('Manter boas práticas de segurança da informação')
        
        return recommendations