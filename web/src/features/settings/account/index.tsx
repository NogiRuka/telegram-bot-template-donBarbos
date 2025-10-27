import { ContentSection } from '../components/content-section'
import { AccountForm } from './account-form'

export function SettingsAccount() {
  return (
    <ContentSection
      title='账户'
      desc='更新您的账户设置。设置您的首选语言和时区。'
    >
      <AccountForm />
    </ContentSection>
  )
}
